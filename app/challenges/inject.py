import random
import time
import string
import json
from pathlib import Path

from config import REDIS, INJECT_CHALLANGE_SCRIPT, INJECT_CHALLANGE_UNVERFIED_TIME_LIMIT, INJECT_CHALLANGE_SCRIPT_LIFETIME, INJECT_CHALLANGE_SCRIPT_AMOUNT, getLogger
from app.challenges import Script as BaseScript
from fastapi.responses import JSONResponse

from ml.session import Session

class InjectChallange:
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
            session = data.get('session').replace('/', '').replace('\\', '').replace('.', '')
            
            file = Path('./sessions/') / (str(self.ray.getShortID() + '.' + str(session)) + '.json')
            if file.exists():
                content = json.loads(file.read_text())
            else:
                content = {'data': [], 'ray': self.ray.dump()}
            
            if(event == 'session_end'):
                if len(content['data']) > 0 and content['data'][-1]['event'] == 'session_end':
                    return JSONResponse({'ok': True})
                
                session = Session()
                print('predict', session.predict(data))
                print('ip', self.ray.ip)
                
            content['data'].append(data)
            file.write_text(json.dumps(content))
            
            if event == 'session_end':
                print('[' + self.ray.requestType + '] Got full session: ' + str(file))
        except Exception as e:
            self.logger.exception(e)

        return JSONResponse({'ok': True})
        
    def getInjectCode(self):
        return ('<script src="/' + str(self.script.getScriptFilename()) + '"></script>').encode()
    
    def getScriptCode(self):
        return 'const SESSION_ID="' + self.getString(time.time_ns(), 32) + '";' + self.script.getCode()
    
    def getScript(self):
        script = Script()
        
        if self.ray.injectChallangeID is not None and REDIS.exists('challenges:inject:' + str(self.ray.injectChallangeID)):
            script.load(self.ray.injectChallangeID, json.loads(REDIS.get('challenges:inject:' + str(self.ray.injectChallangeID))))
            return script
        
        keys = REDIS.keys('challenges:inject:*')
        if len(keys) >= INJECT_CHALLANGE_SCRIPT_AMOUNT:
            random.seed(time.time_ns())
            random.shuffle(keys)
            
            scriptKey = None
            for key in keys:
                if REDIS.ttl(key) > INJECT_CHALLANGE_SCRIPT_LIFETIME / 2:
                    scriptKey = key.decode()
                    break
                
            if scriptKey is not None:
                scriptID = scriptKey.split(':')[-1]
                self.ray.injectChallangeID = scriptID
                self.ray.save()
                script.load(scriptID, json.loads(REDIS.get(scriptKey)))
                return script
        
        script.generate()
        self.ray.injectChallangeID = script.encryptionKey
        self.ray.save()
        return script
    
    def getString(self, seed, length):
        random.seed(seed)
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    
class Script(BaseScript):
    VARIABLES = []
    
    def save(self):
        REDIS.set('challenges:inject:' + str(self.encryptionKey), json.dumps(self.dump()), INJECT_CHALLANGE_SCRIPT_LIFETIME)
    
    def getRawCode(self):
        return INJECT_CHALLANGE_SCRIPT
    
    