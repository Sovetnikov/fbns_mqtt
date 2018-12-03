import asyncio
import calendar
import json
import os
import struct
import time
import uuid
import zlib
from datetime import datetime
from os import getcwd
from os.path import relpath
from urllib.parse import urlsplit, parse_qs

from dateutil.relativedelta import relativedelta
from gmqtt import Client
from gmqtt.client import logger
from gmqtt.mqtt.connection import MQTTConnection
from gmqtt.mqtt.constants import MQTTCommands
from gmqtt.mqtt.handler import _empty_callback
from gmqtt.mqtt.package import PackageFactory
from gmqtt.mqtt.protocol import MQTTProtocol
from gmqtt.mqtt.utils import pack_variable_byte_integer
from thriftpy.protocol import TCompactProtocol
from thriftpy.transport import TMemoryBuffer
import thriftpy

ABSOLUTE_PATH = lambda x: os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), x))


file_path_rel = relpath(ABSOLUTE_PATH('connect.thrift'), getcwd())
thrift = thriftpy.load(file_path_rel, module_name="connect_thrift")


class FBNSAuth(object):
    def __init__(self, data={}):
        self.userId = int(data.get('ck', 0))
        self.password = data.get('cs', '')
        self.deviceSecret = data.get('ds', '')
        self.deviceId = data.get('di', '')

        if self.deviceId:
            self.clientId = self.deviceId[20:]
        else:
            self.clientId = str(uuid.uuid4())[20:]


def _spop(d, k):
    if k in d:
        return d.pop(k)
    return None


class FBNSPush(object):
    def __init__(self, data):
        self.token = _spop(data, 'token')
        self.connectionKey = _spop(data, 'ck')
        self.packageName = _spop(data, 'pn')
        self.collapseKey = _spop(data, 'cp')
        self.payload = _spop(data, 'fbpushnotif')
        self.notificationId = _spop(data, 'nid')
        self.isBuffered = _spop(data, 'bu')
        self.viewId = _spop(data, 'view_id')
        self.numEndpoints = _spop(data, 'num_endpoints')

        if data:
            raise Exception('FBNSPush unexpected data: {data}'.format(**locals))


class FBNSConnectPackageFactor(PackageFactory):
    @classmethod
    def build_package(cls, fbns_auth: FBNSAuth, clean_session, keepalive, protocol, will_message=None, **kwargs):
        keepalive = 900

        connect_payload = thrift.Connect()
        connect_payload.clientIdentifier = fbns_auth.clientId

        client_info = thrift.ClientInfo()
        client_info.userId = fbns_auth.userId
        client_info.userAgent = '[FBAN/MQTT;FBAV/64.0.0.14.96;FBBV/125398467;FBDM/{density=4.0,width=1440,height=2392};FBLC/en_US;FBCR/;FBMF/LGE;FBBD/lge;FBPN/com.instagram.android;FBDV/RS988;FBSV/6.0.1;FBLR/0;FBBK/1;FBCA/armeabi-v7a:armeabi;]'
        client_info.clientCapabilities = 439
        client_info.endpointCapabilities = 128
        client_info.publishFormat = 1
        client_info.noAutomaticForeground = True
        client_info.makeUserAvailableInForeground = False
        client_info.deviceId = fbns_auth.deviceId
        client_info.isInitiallyForeground = False
        client_info.networkType = 1
        client_info.networkSubtype = 0

        last_monday = datetime.now() - relativedelta(weekday=calendar.MONDAY, hour=0, minute=0, second=0, microsecond=0)
        last_monday = last_monday.timestamp()
        session_id = int((time.time() - last_monday) * 1000)

        client_info.clientMqttSessionId = session_id
        client_info.subscribeTopics = [int(FBNSMQTTMQTTClient.MESSAGE_TOPIC_ID), int(FBNSMQTTMQTTClient.REG_RESP_TOPIC_ID)]
        client_info.clientType = 'device_auth'
        client_info.appId = 567310203415052  # Const
        client_info.deviceSecret = fbns_auth.deviceSecret
        client_info.clientStack = 3

        connect_payload.clientInfo = client_info
        connect_payload.password = fbns_auth.password

        trans = TMemoryBuffer()
        p = TCompactProtocol(trans)
        p.write_struct(connect_payload)

        data = trans.getvalue()
        prop_bytes = zlib.compress(data, level=9)

        remaining_length = 2 + len(protocol.proto_name) + 1 + 1 + 2

        connect_flags = 0
        clean_session = True
        if clean_session:
            connect_flags |= 0x02

        connect_flags |= 0x80  # username
        connect_flags |= 0x40  # password

        command = MQTTCommands.CONNECT
        packet = bytearray()
        packet.append(command)

        remaining_length += len(prop_bytes)

        packet.extend(pack_variable_byte_integer(remaining_length))
        packet.extend(struct.pack("!H" + str(len(protocol.proto_name)) + "sBBH",
                                  len(protocol.proto_name),
                                  protocol.proto_name,
                                  protocol.proto_ver,
                                  connect_flags,
                                  keepalive))

        packet.extend(prop_bytes)

        return packet


class FBNSMQTTProtocol(MQTTProtocol):
    proto_name = b'MQTToT'
    proto_ver = 3

    async def send_auth_package(self, fbns_auth, clean_session, keepalive, will_message=None, **kwargs):
        pkg = FBNSConnectPackageFactor.build_package(fbns_auth, clean_session, keepalive, self, will_message=will_message, **kwargs)
        self.write_data(pkg)


class FBNSMQTTConnection(MQTTConnection):
    @classmethod
    async def create_connection(cls, host, port, ssl, clean_session, keepalive, loop=None):
        loop = loop or asyncio.get_event_loop()
        transport, protocol = await loop.create_connection(FBNSMQTTProtocol, host, port, ssl=ssl)
        return FBNSMQTTConnection(transport, protocol, clean_session, keepalive)

    async def auth(self, fbns_auth, will_message=None, **kwargs):
        await self._protocol.send_auth_package(fbns_auth, self._clean_session,
                                               self._keepalive, will_message=will_message, **kwargs)

    def _keep_connection(self):
        super()._keep_connection()
        logger.debug('[KEEP ALIVE]')


FBNSConnAckReturnCodes = {
    0: [
        'Connection accepted',
        '',
    ],
    1: [
        'Unacceptable protocol version',
        'The Server does not support the level of the MQTT protocol requested by the client.',
    ],
    2: [
        'Identifier rejected',
        'The client identifier is correct UTF-8 but not allowed by the server.',
    ],
    3: [
        'Server unavailable',
        'The network connection has been made but the MQTT service is unavailable',
    ],
    4: [
        'Bad user name or password',
        'The data in the user name or password is malformed.',
    ],
    5: [
        'Not authorized',
        'The client is not authorized to connect.',
    ],
}


class FBNSMQTTClient(Client):
    # MQTT Constants.
    PACKAGE_NAME = 'com.instagram.android'

    # Facebook Constants
    FACEBOOK_ANALYTICS_APPLICATION_ID = '567067343352427'

    MESSAGE_TOPIC = '/fbns_msg'
    MESSAGE_TOPIC_ID = '76'

    REG_REQ_TOPIC = '/fbns_reg_req'
    REG_REQ_TOPIC_ID = '79'

    REG_RESP_TOPIC = '/fbns_reg_resp'
    REG_RESP_TOPIC_ID = '80'

    def __init__(self, *args, **kwargs):
        super().__init__(client_id='', *args, **kwargs)
        self.fbns_auth = FBNSAuth()

        self._on_fbns_token_callback = _empty_callback
        self._on_fbns_auth_callback = _empty_callback
        self._on_fbns_message_callback = _empty_callback

    @property
    def on_fbns_message(self):
        return self._on_fbns_message_callback

    @on_fbns_message.setter
    def on_fbns_message(self, cb):
        if not callable(cb):
            raise ValueError
        self._on_fbns_message_callback = cb

    @property
    def on_fbns_auth(self):
        return self._on_fbns_auth_callback

    @on_fbns_auth.setter
    def on_fbns_auth(self, cb):
        if not callable(cb):
            raise ValueError
        self._on_fbns_auth_callback = cb

    @property
    def on_fbns_token(self):
        return self._on_fbns_token_callback

    @on_fbns_token.setter
    def on_fbns_token(self, cb):
        if not callable(cb):
            raise ValueError
        self._on_fbns_token_callback = cb

    def on_message(self, _, topic, payload, qos, properties):
        payload = zlib.decompress(payload)
        payload = json.loads(payload)
        if topic == self.MESSAGE_TOPIC_ID:
            push = FBNSPush(payload)
            self._on_fbns_message(push)
        elif topic == self.REG_RESP_TOPIC_ID:
            self._on_fbns_register(payload)
        else:
            logger.debug('[UNKNOWN MESSAGE] {topic}, {payload}'.format(**locals()))

    def _on_fbns_message(self, payload):
        # It's instagram event
        logger.debug('[FBNS_MSG] {payload}'.format(**locals()))
        self.on_fbns_message(payload)

    def _on_fbns_register(self, payload):
        # Sucsessuf registered in FBNS and we got notification token for Instagram API registration
        if payload.get('error', None):
            error = payload['error']
            raise Exception('FBNS Register error message: {error}'.format(**logger))
        token = payload.get('token')
        logger.debug('[REG_RESP_TOPIC] {token}'.format(**locals()))
        self.on_fbns_token(token)

    async def _create_connection(self, host, port, ssl, clean_session, keepalive) -> FBNSMQTTConnection:
        self._reconnect = True
        connection = await FBNSMQTTConnection.create_connection(host, port, ssl, clean_session, keepalive)
        connection.set_handler(self)
        return connection

    def _on_fbns_connack(self, flags, returncode, data):
        if returncode != 0:
            desc = FBNSConnAckReturnCodes.get(returncode, 'Unknown')
            raise Exception('Connack returncode: {returncode} - {desc}'.format(**locals()))
        data = data.decode('utf8')
        logger.debug('[FBNS CONNACK] {data}'.format(**locals()))
        data = json.loads(data)
        self.on_fbns_auth(data)
        self._register()

    def _register(self):
        message = json.dumps(dict(pkg_name=self.PACKAGE_NAME, appid=self.FACEBOOK_ANALYTICS_APPLICATION_ID))
        payload = zlib.compress(message.encode('utf8'), level=9)
        self.publish(self.REG_REQ_TOPIC, payload, qos=1)

    def _handle_connack_packet(self, cmd, packet):
        super()._handle_connack_packet(cmd, packet)
        (flags, returncode) = struct.unpack("!BB", packet[:2])
        if len(packet) < 2:
            raise Exception('Unexpected connack packet without payload')
        payload = packet[4:]
        payload.decode('utf8')
        self._on_fbns_connack(flags, returncode, payload)

    def set_fbns_auth(self, fbns_auth):
        self.fbns_auth = fbns_auth

    async def connect(self, host, port=1883, ssl=False, keepalive=900):
        # Init connection
        self._host = host
        self._port = port
        self._ssl = ssl
        self._keepalive = keepalive

        self._connection = await self._create_connection(
            host, port=self._port, ssl=self._ssl, clean_session=self._clean_session, keepalive=keepalive)

        await self._connection.auth(self.fbns_auth, will_message=self._will_message,
                                    **self._connect_properties)
        await self._connected.wait()

        loop = asyncio.get_event_loop()
        while not await self._persistent_storage.is_empty:
            await loop.create_future()

        if self._error:
            raise self._error
