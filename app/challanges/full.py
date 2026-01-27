from fastapi.responses import Response, JSONResponse
from config import FULL_CHALLANGE_SCRIPT
from app.ray.ray import Status

import hashlib, hmac

class FullChallange:
    def __init__(self, ray):
        self.ray = ray
    
    async def getResponse(self):
        verifyHash = hashlib.sha256(self.ray.id.encode()).hexdigest()
        if self.ray.request.url.path == '/' + verifyHash:
            data = await self.ray.request.json()
            score, logs = self._calcScore(data)
            self.ray.score = score
            self.ray.scoreLogs = logs
            
            if score >= 100:
                return JSONResponse({'ok': False})
            else:
                self.ray.status = Status.VERFIED
                self.ray.save()
                
                return JSONResponse({'ok': True})
        else:
            consts = {
                'VERIFY_HASH': verifyHash
            }
            return Response('<script>' + self._getScript(consts) + '</script>')
        
    def _calcScore(self, data):
        score = 0
        logs = []
        
        bot_vars = data.get('bot_vars', [])
        if len(bot_vars) > 0:
            score += 100
            logs.append(f"Automation variables detected: {bot_vars}")

        webgl = data.get('webgl', {})
        if webgl:
            renderer = webgl.get('renderer', '').lower()
            vendor = webgl.get('vendor', '').lower()
            
            bad_renderers = ['swiftshader', 'llvmpipe', 'virtualbox', 'vmware', 'software adapter', 'mesa', 'microsoft basic render driver']
            for bad in bad_renderers:
                if bad in renderer or bad in vendor:
                    score += 100
                    logs.append(f"Detected VM/Headless Renderer: {renderer}")
                    break

        if data.get('automation', {}).get('webdriver') is True:
            score += 90
            logs.append("Navigator.webdriver is True")
            
        jit_time = data.get('jit_performance', 0)
        if jit_time > 100:
            score += 15
            logs.append(f"Slow JS execution: {jit_time}ms")
            
        canvas = data.get('canvas', {})
        if canvas:
            canvas_time = canvas.get('time', 0)
            if canvas_time > 30:
                score += 15
                logs.append(f"Slow Canvas render: {jit_time}ms")

        screen = data.get('screen', {})
        if screen.get('ow') == 0 or screen.get('oh') == 0:
            score += 80
            logs.append("Window outer dimensions are 0 (Headless)")
        
        if screen.get('iw') == screen.get('ow') and screen.get('ih') == screen.get('oh'):
            score += 40
            logs.append("No browser chrome detected (Inner == Outer size)")

        hw = data.get('hardware', {})
        if hw.get('cores') is not None and hw.get('cores') < 2:
            score += 20
            logs.append("Low CPU cores (< 2)")

        battery = data.get('battery')
        if battery == "not_supported":
            ua = data.get('automation', {}).get('userAgent', '').lower()
            if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
                score += 50
                logs.append("Mobile User-Agent but Battery API not supported")
        elif isinstance(battery, dict):
            if battery.get('level') == 1.0 and battery.get('charging') is True and battery.get('chargingTime') == 0:
                score += 15
                logs.append("Suspicious battery state (Always 100% charging)")

        if data.get('automation', {}).get('plugins') == 0:
            score += 30
            logs.append("No browser plugins detected")

        if data.get('automation', {}).get('isNativeToString') is False:
            score += 100
            logs.append("Function.toString was tampered (Prototyping hack)")

        fonts = data.get('fonts', [])
        if len(fonts) < 3:
            score += 30
            logs.append(f"Too few system fonts: {len(fonts)}")
        
        return score, logs
    
    def _getScript(self, consts):
        script = FULL_CHALLANGE_SCRIPT
        for k, v in consts.items():
            script = script.replace('{{' + k + '}}', v)
        return script