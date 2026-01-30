import random
import time
import string
import json

from config import REDIS, INJECT_CHALLANGE_SCRIPT, INJECT_CHALLANGE_UNVERFIED_TIME_LIMIT, INJECT_CHALLANGE_SCRIPT_LIFETIME, INJECT_CHALLANGE_SCRIPT_AMOUNT

from app.challanges import Script as BaseScript

class InjectChallange:
    def __init__(self, ray):
        self.ray = ray
        self.script = self.getScript()
        
    def getInjectCode(self):
        return ('<script src="/' + str(self.script.getScriptFilename()) + '"></script>').encode()
    
    def getScriptCode(self):
        return self.script.getCode()
    
    def getScript(self):
        script = Script()
        
        if self.ray.injectChallangeID is not None and REDIS.exists('challanges:inject:' + str(self.ray.injectChallangeID)):
            script.load(self.ray.injectChallangeID, json.loads(REDIS.get('challanges:inject:' + str(self.ray.injectChallangeID))))
            return script
        
        keys = REDIS.keys('challanges:inject:*')
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
        REDIS.set('challanges:inject:' + str(self.encryptionKey), json.dumps(self.dump()), INJECT_CHALLANGE_SCRIPT_LIFETIME)
    
    def getRawCode(self):
        return INJECT_CHALLANGE_SCRIPT