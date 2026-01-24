from enum import Enum
from config import REDIS, RAY_LIFETIME, getLogger
import json

class Ray:
    def __init__(self, id = None, request = None):
        self.data = None
        self.request = None

        self.id = id
        self.status = Status.UNVERFIED
        if request is not None:
            self.request = request
            self.ip = self.request.client.host
            self.userAgent = request.headers.get("user-agent")
            
            if len(request.headers.get('x-ja4-app')) == 0 and not request.client.host.startswith('188.127.241.'):
                print(request.client.host)
                print(request.headers.get('user-agent'))

            if request.headers['host'] == 'captcha.qwertyx.host':
                getLogger('debug').info(request.headers.get(''))

    def load(self, data):
        self.id = data['id']
        self.status = Status(data['status'])
        self.data = data
    
    def dump(self):
        return {
            'id': self.id,
            'status': self.status.value,
            'request': {
                'ip': self.ip,
                'user-agent': self.userAgent
            }
        }
    
    def save(self):
        REDIS.set('ray:' + str(self.id), json.dumps(self.dump()), RAY_LIFETIME)

    def verify(self):
        if self.data is not None and self.request is not None:
            if self.data['request']['ip'] != self.ip or self.data['request']['user-agent'] != self.userAgent:
                self.status = Status.UNVERFIED

        if self.status == Status.UNVERFIED:
            self.status = Status.VERFIED
            self.save()

        return self.status
    
    def getShortID(self):
        return self.id[:12] + self.id.split('.')[1]

class Status(Enum):
    UNVERFIED = 'unverfied'
    VERIFING = 'verifing'
    VERFIED = 'verfied'
    CAPTCHA = 'captcha'
    BLOCKED = 'blocked'