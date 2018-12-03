import logging
import os
import pickle
import sys
import asyncio
from datetime import datetime
from instagram_private_api import Client, ClientCookieExpiredError, ClientLoginRequiredError
from dateutil.relativedelta import relativedelta
from fbns_mqtt.fbns_mqtt import FBNSMQTTClient, FBNSAuth

ABSOLUTE_PATH = lambda x: os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), x))
sys.path.append(ABSOLUTE_PATH('.'))
from instagram_notification_data import InstagramNotification

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

STOP = asyncio.Event()

USERNAME = ''
PASSWORD = ''
SETTINGS_FILE = 'fbns_mqtt_settings_{USERNAME}.pickle'.format(**locals())


def save_settings(data):
    with open(SETTINGS_FILE, 'wb') as pickle_file:
        pickle.dump(data, pickle_file)

class ExtendedClient(Client):
    def register_push(self, token):
        endpoint = 'push/register/'
        params = dict(
            device_type='android_mqtt',
            is_main_push_channel=True,
            phone_id=self.phone_id,
            device_token=token,  # fbns_token
            guid=self.uuid,
            users=self.authenticated_user_id,
        )
        params.update(self.authenticated_params)
        res = self._call_api(endpoint, params=params, unsigned=True)
        return res


async def instagram_listener_worker():
    if os.path.exists(ABSOLUTE_PATH(SETTINGS_FILE)):
        with open(ABSOLUTE_PATH(SETTINGS_FILE), mode='rb') as f:
            settings = pickle.load(f)
    else:
        settings = {}

    client = FBNSMQTTClient()

    fbns_auth = settings.get('fbns_auth')
    if fbns_auth:
        client.set_fbns_auth(FBNSAuth(fbns_auth))

    def on_login_callback(client):
        settings['api_settings'] = client.settings
        save_settings(settings)

    def on_fbns_auth(auth):
        settings['fbns_auth'] = auth
        settings['fbns_auth_received'] = datetime.now()
        save_settings(settings)

    def on_fbns_token(token):
        if settings.get('fbns_token', None) == token:
            if 'fbns_token_received' in settings and settings['fbns_token_received'] > datetime.now() - relativedelta(hours=24):
                # Do not register token twice in 24 hours
                return

        device_id = settings.get('device_id')
        try:
            if settings.get('api_settings'):
                client = ExtendedClient(USERNAME, PASSWORD, settings=settings.get('api_settings'))
            else:
                client = ExtendedClient(USERNAME, PASSWORD, on_login=on_login_callback)
        except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
            client = ExtendedClient(USERNAME, PASSWORD, device_id=device_id, on_login=on_login_callback)

        client.register_push(token)

        settings['fbns_token'] = token
        settings['fbns_token_received'] = datetime.now()
        save_settings(settings)

    def on_fbns_message(push):
        if push.payload:
            notification = InstagramNotification(push.payload)
            if notification.collapseKey == 'comment':
                print(notification.message)
            elif notification.collapseKey == 'direct_v2_message':
                print(notification.it)

    client.on_fbns_auth = on_fbns_auth
    client.on_fbns_token = on_fbns_token
    client.on_fbns_message = on_fbns_message

    await client.connect('mqtt-mini.facebook.com', 443, ssl=True, keepalive=900)
    await STOP.wait()
    await client.disconnect()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # task = loop.create_task(instagram_listener_worker())

    try:
        loop.run_until_complete(instagram_listener_worker())
    except asyncio.CancelledError:
        pass
