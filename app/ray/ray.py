from enum import Enum
from config import REDIS, RAY_LIFETIME, JA4_KEY_DETECT, BOT_USERAGENT_KEYWORDS, DB
import json
import time
import ipaddress

class Ray:
    def __init__(self, group, id = None, request = None):
        self.data = None
        self.request = None
        self.group = group
        self.checker = {}
        
        self.requestType = 'human'
        
        self.fullChallengeID = None
        self.injectChallengeID = None
        self.dbID = None
        
        self.score = None
        self.scoreLogs = None
        self.savedScore = None
        self.savedScoreLogs = None
        self.verifyLogs = None
        self.createTime = time.time_ns()
        
        self.appAccuracy = None

        self.id = id
        self.status = Status.UNVERFIED
        if request is not None:
            self.request = request
            self.ip = self.request.headers.get('x-forwarded-for')
            self.userAgent = request.headers.get("user-agent")
            
            self.ja4_fingerprint = request.headers.get('X-JA4-Fingerprint')
            self.ja4_app = request.headers.get('X-JA4-App')
            self.ja4_raw = request.headers.get('X-JA4-Raw')

    def load(self, data):
        self.id = data['id']
        self.status = Status(data['status']) if any(k.value == data['status'] for k in Status) else Status.UNVERFIED
        self.savedScore = data.get('score', None)
        self.savedScoreLogs = data.get('scoreLogs', None)
        self.fullChallengeID = data.get('fullChallengeID', None)
        self.injectChallengeID = data.get('injectChallengeID', None)
        self.createTime = data.get('createTime', time.time_ns())
        self.requestType = data.get('requestType', self.requestType)
        self.dbID = data.get('dbID', None)
        self.data = data
    
    def dump(self):
        return {
            'id': self.id,
            'status': self.status.value,
            'score': self.score if self.score is not None else self.savedScore,
            'scoreLogs': self.scoreLogs if self.scoreLogs is not None else self.savedScoreLogs,
            'appAccuracy': self.appAccuracy,
            'fullChallengeID': self.fullChallengeID,
            'injectChallengeID': self.injectChallengeID,
            'verifyLogs': self.verifyLogs,
            'createTime': self.createTime,
            'requestType': self.requestType,
            'dbID': self.dbID,
            'request': {
                'ip': self.ip,
                'user-agent': self.userAgent,
                'ja4_fingerprint': self.ja4_fingerprint
            }
        }
        
    def saveRequest(self):
        if self.dbID is not None:
            DB.addRequest(self.dbID, time.time_ns(), str(self.request.url), self.status.value)
    
    def save(self):
        if self.dbID is None and not DB.rayExists(self.id, self.group.name):
            self.dbID = DB.addRay(self.id, self.createTime, self.status.value, self.group.name, self.ip, None, None, None, self.userAgent, self.verifyLogs, self.scoreLogs, {})
        REDIS.set('ray:' + self.group.name + ':' + str(self.id), json.dumps(self.dump()), RAY_LIFETIME)
        self.updateDB({'status': self.status.value, 'verify_logs': self.verifyLogs})
        
    def updateDB(self, data):
        DB.updateRay(self.dbID, data)

    def verify(self):
        self.verifyLogs = []
        ip = ipaddress.ip_address(self.ip)
        for subnet in self.group.whitelist:
            if ip in subnet:
                self.status = Status.VERFIED
                self.verifyLogs.append('IP in whitelist')
                self.save()
                return self.status
        
        if self.data is not None and self.request is not None:
            if self.data['request']['ip'] != self.ip or self.data['request']['user-agent'] != self.userAgent:
                self.status = Status.UNVERFIED
                self.verifyLogs.append('Request ip or user agent changed. Status set to Unverfied')
            
            if 'ja4_fingerprint' in self.data['request'] and self.ja4_fingerprint[:6] + 'XX' + self.ja4_fingerprint[8:23] != self.data['request']['ja4_fingerprint'][:6] + 'XX' + self.data['request']['ja4_fingerprint'][8:23]:
                self.status = Status.UNVERFIED
                self.verifyLogs.append('Request JA4 fingerprint changed. Status set to Unverfied')
                
        if self.userAgent == None:
            self.status = Status.BLOCKED
            self.verifyLogs.append('User agent is None')
        
        if self.status not in [Status.JS_CHALLENGE, Status.FULL_JS_CHALLENGE]:
            self.status = Status.FULL_JS_CHALLENGE
        
        # JA4 / UserAgent Filter 
        if self.status == Status.UNVERFIED:
            if len(self.ja4_app) > 0:
                if self.ja4_app.endswith(JA4_KEY_DETECT):
                    self.status = Status.BLOCKED
                    self.verifyLogs.append('Bot detected by JA4 fingerprint')
                else:
                    accuracy = self._getUserAgentAccuracy(self.userAgent, self.ja4_app)
                    self.appAccuracy = accuracy
                    if accuracy < 0.3:
                        self.status = Status.BLOCKED
                        self.verifyLogs.append('Low JA4 App accuracy. Set status to blocked')
                    elif accuracy < 0.7:
                        self.status = Status.FULL_JS_CHALLENGE
                        self.verifyLogs.append('Medium JA4 App accuracy. Set status to FULL JS CHALLENGE')
                    else:
                        self.status = Status.FULL_JS_CHALLENGE
                        self.verifyLogs.append('Normal JA4 App accuracy. Set status to JS CHALLENGE')
            else:
                bot = False
                for word in BOT_USERAGENT_KEYWORDS:
                    if word in self.userAgent:
                        bot = True
                        break
                if bot == True:
                    self.status = Status.BLOCKED
                    self.verifyLogs.append('Bot detected in User-Agent. Set status to Blocked')
                else:
                    self.status = Status.FULL_JS_CHALLENGE
                    self.verifyLogs.append('No JA4 App found, No bot detected. Changed status to FULL_JS_CHALLENGE')
        
        self.save()

        return self.status
    
    def _getUserAgentAccuracy(self, userAgent, ja4App):
        a = 0
        t = 0
        for i in ja4App.split('_'):
            if i in userAgent:
                a += 1
            t += 1
        return a / t
    
    def getShortID(self):
        return self.id[:12] + self.id.split('.')[1]

class Status(Enum):
    UNVERFIED = 'unverfied'
    VERIFING = 'verifing'
    VERFIED = 'verfied'
    FULL_JS_CHALLENGE = 'full_js_challenge'
    JS_CHALLENGE = 'js_challenge'
    BLOCKED = 'blocked'