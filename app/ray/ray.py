from enum import Enum
from config import REDIS, RAY_LIFETIME, JA4_KEY_DETECT, BOT_USERAGENT_KEYWORDS
import json
import pprint
import time
import ipaddress

class Ray:
    def __init__(self, group, id = None, request = None):
        self.data = None
        self.request = None
        self.group = group
        self.checker = {}
        
        self.fullChallangeID = None
        
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
            
            
            # if len(request.headers.get('x-ja4-app')) == 0 and not request.client.host.startswith('188.127.241.'):
            #     print(request.client.host)
            #     print(request.headers.get('user-agent'))

            # if request.headers['host'] == 'captcha.qwertyx.host':
            #     getLogger('debug').info(request.headers.get(''))

    def load(self, data):
        self.id = data['id']
        self.status = Status(data['status']) if any(k.value == data['status'] for k in Status) else Status.UNVERFIED
        self.savedScore = data.get('score', None)
        self.savedScoreLogs = data.get('scoreLogs', None)
        self.fullChallangeID = data.get('fullChallangeID', None)
        self.createTime = data.get('createTime', time.time_ns())
        self.data = data
    
    def dump(self):
        return {
            'id': self.id,
            'status': self.status.value,
            'score': self.score,
            'scoreLogs': self.scoreLogs,
            'appAccuracy': self.appAccuracy,
            'fullChallangeID': self.fullChallangeID,
            'verifyLogs': self.verifyLogs,
            'createTime': self.createTime,
            'request': {
                'ip': self.ip,
                'user-agent': self.userAgent,
                'ja4_fingerprint': self.ja4_fingerprint
            }
        }
    
    def save(self):
        REDIS.set('ray:' + self.group.name + ':' + str(self.id), json.dumps(self.dump()), RAY_LIFETIME)

    def verify(self):
        pp = pprint.PrettyPrinter(indent=4)
        
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
                self.verifyLogs.append('Request JA4 fingerprint changes. Status set to Unverfied')
                # self.status = Status.FULL_JS_CHALLANGE
                # return self.status
                
        if self.userAgent == None:
            self.status = Status.BLOCKED
            self.verifyLogs.append('User agent is None')
           
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
                        self.status = Status.FULL_JS_CHALLANGE
                        self.verifyLogs.append('Medium JA4 App accuracy. Set status to FULL JS CHALLANGE')
                    else:
                        self.status = Status.JS_CHALLANGE
                        self.verifyLogs.append('Normal JA4 App accuracy. Set status to JS CHALLANGE')
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
                    self.status = Status.FULL_JS_CHALLANGE
                    self.verifyLogs.append('No JA4 App found, No bot detected. Changed status to FULL_JS_CHALLANGE')
            
        # if self.status == Status.BLOCKED or self.status == Status.FULL_JS_CHALLANGE:
        #     pp.pprint(self.request.url.path)
        #     pp.pprint(self.dump())
        
        # if self.status == Status.UNVERFIED:
        # if self.group.name == 'dev' and self.status not in [Status.VERFIED]:
        #     if self.status != Status.BLOCKED:
        #         self.status = Status.FULL_JS_CHALLANGE
        # else:
        #     self.status = Status.VERFIED
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
    FULL_JS_CHALLANGE = 'full_js_challange'
    JS_CHALLANGE = 'js_challange'
    BLOCKED = 'blocked'