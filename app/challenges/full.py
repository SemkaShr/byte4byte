from fastapi.responses import Response, JSONResponse
from config import FULL_CHALLANGE_SCRIPT, REDIS, FULL_CHALLANGE_SCRIPT_AMOUNT, FULL_CHALLANGE_SCRIPT_LIFETIME
from app.ray.ray import Status
from app.challenges import Script as BaseScript

import time
import random
import json

class FullChallange:
    def __init__(self, ray):
        self.ray = ray
    
    async def getResponse(self):
        script = self.getScript()
        if self.ray.request.url.path == script.endpoint:
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
                self.ray.status = Status.JS_CHALLANGE
                self.ray.requestType = 'bot'
                self.ray.save()
                
                return JSONResponse({'ok': True})
            else:
                self.ray.status = Status.JS_CHALLANGE
                self.ray.save()
                
                return JSONResponse({'ok': True})
        else:
            return Response('<script>' + script.getCode() + '</script>', 403) 
                
    def getScript(self):
        script = Script()
        
        if self.ray.fullChallangeID is not None and REDIS.exists('challenges:full:' + str(self.ray.fullChallangeID)):
            script.load(self.ray.fullChallangeID, json.loads(REDIS.get('challenges:full:' + str(self.ray.fullChallangeID))))
            return script
        
        keys = REDIS.keys('challenges:full:*')
        if len(keys) >= FULL_CHALLANGE_SCRIPT_AMOUNT:
            random.seed(time.time_ns())
            random.shuffle(keys)
            
            scriptKey = None
            for key in keys:
                if REDIS.ttl(key) > FULL_CHALLANGE_SCRIPT_LIFETIME / 2:
                    scriptKey = key.decode()
                    break
                
            if scriptKey is not None:
                scriptID = scriptKey.split(':')[-1]
                self.ray.fullChallangeID = scriptID
                self.ray.save()
                script.load(scriptID, json.loads(REDIS.get(scriptKey)))
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
            score += 50
            reasons.append(f"WebGL is undefiend")
            
        if data.get(script.get('WEBDRIVER')) is True:
            score += 90
            reasons.append("Navigator.webdriver is True")
            
        jit_time = data.get(script.get('JIT_PERFORMANCE'), 101)
        if jit_time > 100:
            score += 20
            reasons.append(f"Slow JS execution: {jit_time}ms")
            
        if data.get(script.get('SCREEN_OW')) == 0 or data.get(script.get('SCREEN_OH')) == 0:
            score += 80
            reasons.append("Window outer dimensions are 0 (Headless)")
        
        if data.get(script.get('SCREEN_IW')) == data.get(script.get('SCREEN_OW')) and data.get(script.get('SCREEN_IH')) == data.get(script.get('SCREEN_OH')):
            score += 15
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
        # elif isinstance(battery, dict):
        #     if battery.get(script.get('BATTERY_LEVEL')) == 1.0 and battery.get(script.get('BATTERY_CHARGING')) is True and battery.get(script.get('BATTERY_CHARGING_TIME')) == 0:
        #         score += 0
        #         reasons.append("Suspicious battery state (Always 100% charging)")
        
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
    
class Script(BaseScript):
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
        
    def save(self):
        REDIS.set('challenges:full:' + str(self.encryptionKey), json.dumps(self.dump()), FULL_CHALLANGE_SCRIPT_LIFETIME)
    
    def getRawCode(self):
        return FULL_CHALLANGE_SCRIPT