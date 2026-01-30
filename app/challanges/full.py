from fastapi.responses import Response, JSONResponse
from config import FULL_CHALLANGE_SCRIPT, OBFUSCATOR_JS, REDIS, FULL_CHALLANGE_SCRIPT_AMOUNT, FULL_CHALLANGE_SCRIPT_LIFETIME
from app.ray.ray import Status

import hashlib
import time
import random
import string
import json
import base64
from Crypto.Cipher import AES

class FullChallange:
    def __init__(self, ray):
        self.ray = ray
    
    async def getResponse(self):
        script = self.getScript()
        if self.ray.request.url.path == '/' + script.hash and self.ray.request.method == 'POST':
            body = await self.ray.request.body()
            data = script.decrypt(body)
            
            score, logs = self.calcScore(data, script)
            self.ray.score = score
            self.ray.scoreLogs = logs
            
            print('----------')
            print(self.ray.ip)
            print(score)
            print(logs)
            print('----------')
            
            if score >= 100:
                self.ray.status = Status.BLOCKED
                self.ray.save()
                
                return JSONResponse({'ok': False})
            else:
                self.ray.status = Status.VERFIED
                self.ray.save()
                
                return JSONResponse({'ok': True})
        else:
            return Response('<script>' + script.code + '</script>', 403) 
                
    def getScript(self):
        script = Script()
        
        if self.ray.fullChallangeID is not None and REDIS.exists('challanges:full:' + str(self.ray.fullChallangeID)):
            script.load(self.ray.fullChallangeID, json.loads(REDIS.get('challanges:full:' + str(self.ray.fullChallangeID))))
            return script
        
        keys = REDIS.keys('challanges:full:*')
        if len(keys) >= FULL_CHALLANGE_SCRIPT_AMOUNT:
            random.seed(time.time_ns())
            random.shuffle(keys)
            
            scriptKey = None
            for key in keys:
                if REDIS.ttl(key) > FULL_CHALLANGE_SCRIPT_LIFETIME / 2:
                    scriptKey = key
                    break
                
            if scriptKey is not None:
                scriptID = scriptKey.split(':')[-1]
                self.ray.fullChallangeID = scriptID
                self.ray.save()
                script.load(scriptID, REDIS.get(scriptKey))
                return script
        
        script.generate()
        self.ray.fullChallangeID = script.encryptionKey
        self.ray.save()
        return script
            
        
    def calcScore(self, data, script):
        score = 0
        reasons = []
        
        botVars = data.get(script.get('BOTVARS'), [])
        if len(botVars) > 0:
            score += 100
            reasons.append(f"Automation variables detected: {botVars}")
        
        if data.get(script.get('CORES'), 0) <= 2:
            score += 20
            reasons.append("Low CPU cores (<= 2)")
            
        webgl = data.get(script.get('WEBGL'), {})
        if webgl:
            renderer = webgl.get(script.get('WEBGL_RENDERER'), '').lower()
            vendor = webgl.get(script.get('WEBGL_VENDOR'), '').lower()
            
            bad_renderers = ['swiftshader', 'llvmpipe', 'virtualbox', 'vmware', 'software adapter', 'mesa', 'microsoft basic render driver']
            for bad in bad_renderers:
                if bad in renderer or bad in vendor:
                    score += 100
                    reasons.append(f"Detected VM/Headless Renderer: {renderer}")
                    break
        else:
            score += 100
            reasons.append(f"WebGL is undefiend")
            
        if data.get(script.get('WEBDRIVER')) is True:
            score += 90
            reasons.append("Navigator.webdriver is True")
            
        jit_time = data.get(script.get('JIT_PERFORMANCE'), 101)
        if jit_time > 100:
            score += 15
            reasons.append(f"Slow JS execution: {jit_time}ms")
            
        if data.get(script.get('SCREEN_OW')) == 0 or data.get(script.get('SCREEN_OH')) == 0:
            score += 80
            reasons.append("Window outer dimensions are 0 (Headless)")
        
        if data.get(script.get('SCREEN_IW')) == data.get(script.get('SCREEN_OW')) and data.get(script.get('SCREEN_IH')) == data.get(script.get('SCREEN_OH')):
            score += 40
            reasons.append("No browser chrome detected (Inner == Outer size)")
        
        if self.ray.userAgent != data.get(script.get('USERAGENT'), ''):
            score += 100
            reasons.append("User agant is different")
        
        battery = data.get(script.get('BATTERY'))
        if battery == "ns":
            ua = data.get(script.get('USERAGENT'), '').lower()
            if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
                score += 50
                reasons.append("Mobile User-Agent but Battery API not supported")
        elif isinstance(battery, dict):
            if battery.get(script.get('BATTERY_LEVEL')) == 1.0 and battery.get(script.get('BATTERY_CHARGING')) is True and battery.get(script.get('BATTERY_CHARGING_TIME')) == 0:
                score += 15
                reasons.append("Suspicious battery state (Always 100% charging)")
        
        if data.get(script.get('PLUGINS')) == 0:
            score += 30
            reasons.append("No browser plugins detected")

        if data.get(script.get('IS_NATIVE_TO_STR')) is False:
            score += 100
            reasons.append("Function.toString was tampered (Prototyping hack)")

        fonts = data.get(script.get('FONTS'), [])
        if len(fonts) < 3:
            score += 30
            reasons.append(f"Too few system fonts: {len(fonts)}")
        
        return score, reasons
    
class Script:
    VARIABLES = [
        'CANVAS',
        'BATTERY',
        'FONTS',
        'BOTVARS',
        'JIT_PERFORMANCE',
        'WEBDRIVER',
        'PLUGINS',
        'LANGUAGES',
        'IS_NATIVE_TO_STR',
        'SCREEN_W',
        'SCREEN_H',
        'SCREEN_AW',
        'SCREEN_AH',
        'SCREEN_IW',
        'SCREEN_IH',
        'SCREEN_OW',
        'SCREEN_OH',
        'SCREEN_RATIO',
        'BATTERY_LEVEL',
        'BATTERY_CHARGING',
        'BATTERY_CHARGING_TIME',
        'WEBGL',
        'WEBGL_VENDOR',
        'WEBGL_RENDERER',
        'CORES',
        'MEMORY',
        'PLATFORM',
        'USERAGENT'
    ]
    
    def __init__(self):
        self.code = None
        self.rawCode = None
        self.varNames = None
        
    def load(self, key, data):
        if len(key) != 32:
            return False
        self.encryptionKey = key
        self.hash = hashlib.sha256(self.encryptionKey.encode()).hexdigest()
        
        self.code = data.get('code', None)
        self.varNames = data.get('vars', None)
        
        return self
    
    def decrypt(self, data):
        encrypted = base64.b64decode(data)
    
        cipher = AES.new(
            self.encryptionKey.encode()[:32], 
            AES.MODE_CBC, 
            iv=bytes(16)
        )

        decrypted = cipher.decrypt(encrypted)
        padding_length = decrypted[-1]
        decrypted = decrypted[:-padding_length]
        
        return json.loads(decrypted.decode())

            
    def dump(self):
        return {
            'code': self.code,
            'vars': self.varNames
        }
        
    def getCode(self):
        if self.code == None:
            self.varNames = self._genNames()
        
            for i, key in enumerate(self.VARIABLES):
                self.rawCode = self.rawCode.replace('{{' + str(key) + '}}', self.varNames[i])
                
            self.rawCode = self.rawCode.replace('{{SCRIPT_HASH_ID}}', self.hash)
            self.rawCode = self.rawCode.replace('{{SCRIPT_KEY}}', self.encryptionKey)
            
            self.code = OBFUSCATOR_JS.obfuscate(self.rawCode, {
                'renameGlobals': True,
                'compact': True,
                'renameProperties': False,
                'splitStrings': False,
                'numbersToExpressions': True,
                'transformObjectKeys': False,
                'reservedNames': ['iv', 'Uint8Array'],
                'selfDefending': True
            }).getObfuscatedCode()
        return self.code
        
    def save(self):
        REDIS.set('challanges:full:' + str(self.encryptionKey), json.dumps(self.dump()), FULL_CHALLANGE_SCRIPT_LIFETIME)
    
    def generate(self):
        self.encryptionKey = self._genString(32)
        self.hash = hashlib.sha256(self.encryptionKey.encode()).hexdigest()
        self.rawCode = FULL_CHALLANGE_SCRIPT
        self.code = self.getCode()
        self.save()
        return self
    
    def get(self, key):
        if self.varNames == None:
            return None
        return self.varNames[self.VARIABLES.index(key)]
    
    def _genNames(self):
        varLen = max(len(self.VARIABLES) // len(string.ascii_letters), 1)
        names = []
        for i in range(len(self.VARIABLES)):
            name = ''
            n = i
            for _ in range(varLen):
                n, idx = divmod(n, len(string.ascii_letters))
                name += string.ascii_letters[idx]
            names.append(name)
            
        random.seed(self.encryptionKey)
        random.shuffle(names)
            
        return names
    
    def _genString(self, length):
        random.seed(time.time_ns())
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))