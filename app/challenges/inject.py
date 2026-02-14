import random
import time
import string
import json
from pathlib import Path

from config import REDIS, INJECT_CHALLENGE_SCRIPT, COLLECT_SESSIONS, INJECT_CHALLENGE_SCRIPT_LIFETIME, INJECT_CHALLENGE_SCRIPT_AMOUNT, getLogger
from app.challenges import Script as BaseScript
from fastapi.responses import JSONResponse
from app.ray.ray import Status

from ml.session import Session

class InjectChallenge:
    def __init__(self, ray):
        self.ray = ray
        self.script = self.getScript()
        self.logger = getLogger('b4b.challenges.inject')
        
    async def getResponse(self):
        body = await self.ray.request.body()
        data = self.script.decrypt(body)
        
        try:
            event = data.get('event')
            if data['session'] == None:
                return JSONResponse({'ok': False})
            
            if COLLECT_SESSIONS:
                session = data.get('session').replace('/', '').replace('\\', '').replace('.', '')
                
                file = Path('./sessions/') / (str(self.ray.getShortID() + '.' + str(session)) + '.json')
                if file.exists():
                    content = json.loads(file.read_text())
                else:
                    content = {'data': [], 'ray': self.ray.dump()}
                
                if event == 'session_end':
                    if len(content['data']) > 0 and content['data'][-1]['event'] == 'session_end':
                        return JSONResponse({'ok': True})
                    
                    session = Session()
                    print('predict', session.predict(data))
                    print('ip', self.ray.ip)
                    
                content['data'].append(data)
                file.write_text(json.dumps(content))
                
                if event == 'session_end':
                    print('[' + self.ray.requestType + '] Got full session: ' + str(file))
            else:
                if event == 'session_end':
                    session = Session()
                    predict = session.predict(data)
                    
                    self.ray.updateDB({'extra_data': {'predict': float(predict[1]), 'inject_challenge_status': 'verfied'}})
                    if predict[1] >= 0.5:
                        self.ray.updateDB({'inject_challenge_status': 'verfied'})
                        self.ray.status = Status.VERFIED
                        self.ray.save()
                    else:
                        self.ray.updateDB({'inject_challenge_status': 'blocked'})
        except Exception as e:
            self.logger.exception(e)

        return JSONResponse({'ok': True})
        
    def getInjectCode(self):
        return ('<script src="/' + str(self.script.getScriptFilename()) + '"></script>').encode()
    
    def getScriptCode(self):
        return 'const SESSION_ID="' + self.getString(time.time_ns(), 32) + '";' + self.script.getCode()
    
    def getScript(self):
        script = Script()
        
        if self.ray.injectChallengeID is not None and REDIS.exists('challenges:inject:' + str(self.ray.injectChallengeID)):
            script.load(self.ray.injectChallengeID, json.loads(REDIS.get('challenges:inject:' + str(self.ray.injectChallengeID))))
            return script
        
        keys = REDIS.keys('challenges:inject:*')
        if len(keys) >= INJECT_CHALLENGE_SCRIPT_AMOUNT:
            random.seed(time.time_ns())
            random.shuffle(keys)
            
            scriptKey = None
            for key in keys:
                if REDIS.ttl(key) > INJECT_CHALLENGE_SCRIPT_LIFETIME / 2:
                    scriptKey = key.decode()
                    break
                
            if scriptKey is not None:
                scriptID = scriptKey.split(':')[-1]
                self.ray.injectChallengeID = scriptID
                self.ray.save()
                script.load(scriptID, json.loads(REDIS.get(scriptKey)))
                return script
        
        script.generate()
        self.ray.injectChallengeID = script.encryptionKey
        self.ray.save()
        return script
    
    def getString(self, seed, length):
        random.seed(seed)
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    
class Script(BaseScript):
    VARIABLES = []
    
    def save(self):
        REDIS.set('challenges:inject:' + str(self.encryptionKey), json.dumps(self.dump()), INJECT_CHALLENGE_SCRIPT_LIFETIME)
    
    def getRawCode(self):
        return INJECT_CHALLENGE_SCRIPT
    
    