struct ClientInfo {
  1:  i64       userId,
  2:  string    userAgent,
  3:  i64       clientCapabilities,
  4:  i64       endpointCapabilities,
  5:  i32       publishFormat,
  6:  bool      noAutomaticForeground,
  7:  bool      makeUserAvailableInForeground,
  8:  string    deviceId,
  9:  bool      isInitiallyForeground,
  10: i32       networkType,
  11: i32       networkSubtype,
  12: i64       clientMqttSessionId,
  13: string    clientIpAddress,
  14: list<i32> subscribeTopics,
  15: string    clientType,
  16: i64       appId,
  17: bool      overrideNectarLogging,
  18: string    connectTokenHash,
  19: string    regionPreference,
  20: string    deviceSecret,
  21: byte        clientStack,
  22: i64       fbnsConnectionKey,
  23: string    fbnsConnectionSecret,
  24: string    fbnsDeviceId,
  25: string    fbnsDeviceSecret
}

struct GetIrisDiffs {
  1:  string syncToken,
  2:  i64    lastSeqId,
  3:  i32    maxDeltasAbleToProcess,
  4:  i32    deltaBatchSize,
  5:  string encoding,
  6:  string queueType,
  7:  i32    syncApiVersion,
  8:  string deviceId,
  9:  string deviceParams,
  10: string queueParams,
  11: i64    entityFbid,
  12: i64    syncTokenLong
}

struct ProxygenInfo {
  1: string ipAddr,
  2: string hostName,
  3: string vipAddr
}

struct CombinedPublish {
  1: string topic,
  2: i32    messageId,
  3: string payload
}

struct Connect {
  1:  string                clientIdentifier,
  2:  string                willTopic,
  3:  string                willMessage,
  4:  ClientInfo            clientInfo,
  5:  string                password,
  6:  list<string>          getDiffsRequests,
  7:  list<ProxygenInfo>    proxygenInfo,
  8:  list<CombinedPublish> combinedPublishes,
  9:  string                zeroRatingTokenHash,
  10: map<string,string>    appSpecificInfo
}