from enum import Enum
from config import REDIS, RAY_LIFETIME, getLogger, JA4_KEY_DETECT, BOT_USERAGENT_KEYWORDS, BOT_EXCLUDE
import json
import pprint

class Ray:
    def __init__(self, group, id = None, request = None):
        self.data = None
        self.request = None
        self.group = group
        self.checker = {}
        
        self.score = None
        self.scoreLogs = None
        self.savedScore = None
        self.savedScoreLogs = None
        
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
        self.status = Status(data['status'])
        self.savedScore = data['score'] if 'score' in data else None
        self.savedScoreLogs = data['scoreLogs'] if 'scoreLogs' in data else None
        self.data = data
    
    def dump(self):
        return {
            'id': self.id,
            'status': self.status.value,
            'score': self.score,
            'scoreLogs': self.scoreLogs,
            'appAccuracy': self.appAccuracy,
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
        
        if self.ip in self.group.whitelist:
            self.status = Status.VERFIED
            self.save()
            return self.status
        
        if self.data is not None and self.request is not None:
            if self.data['request']['ip'] != self.ip or self.data['request']['user-agent'] != self.userAgent:
                self.status = Status.UNVERFIED
            
            if 'ja4_fingerprint' in self.data['request'] and self.ja4_fingerprint[:6] + 'XX' + self.ja4_fingerprint[8:23] != self.data['request']['ja4_fingerprint'][:6] + 'XX' + self.data['request']['ja4_fingerprint'][8:23]:
                self.status = Status.UNVERFIED
                # self.status = Status.CAPTCHA
                # return self.status
           
        # First Filter 
        if self.status == Status.UNVERFIED:
            if len(self.ja4_app) > 0:
                if self.ja4_app.endswith(JA4_KEY_DETECT):
                    self.status = Status.BLOCKED
                else:
                    accuracy = self._getUserAgentAccuracy(self.userAgent, self.ja4_app)
                    self.appAccuracy = accuracy
                    if accuracy < 0.3:
                        self.status = Status.BLOCKED
                    elif accuracy < 0.7:
                        self.status = Status.CAPTCHA
                    else:
                        self.status = Status.JS_CHALLANGE
            else:
                bot = None
                for word in BOT_EXCLUDE:
                    if word in self.userAgent:
                        bot = False
                        break
                if bot == None:
                    bot = False
                    for word in BOT_USERAGENT_KEYWORDS:
                        if word in self.userAgent:
                            bot = True
                            break
                if bot == True:
                    self.status = Status.BLOCKED
                else:
                    self.status = Status.CAPTCHA
            
            pp.pprint(self.request.url.path)
            pp.pprint(self.dump())
        
        # if self.status == Status.UNVERFIED:
        self.status = Status.VERFIED
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
    CAPTCHA = 'captcha'
    JS_CHALLANGE = 'js_challange'
    BLOCKED = 'blocked'