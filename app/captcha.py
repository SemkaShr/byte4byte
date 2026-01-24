from fastapi.responses import Response
from config import CAPTCHA_IMGS, CAPTCHA_PAGE
import random
import base64

import hashlib, hmac

class Captcha:
    def __init__(self, ray):
        self.ray = ray
    
    def getResponse(self):
        random.seed(self.ray.id)
        targetObject = random.choice(list(CAPTCHA_IMGS.keys()))

        objects = []
        for _ in range(random.randint(2,4)):
            while True:
                img = random.choice(CAPTCHA_IMGS[targetObject])
                if not img in objects:
                    objects.append(img)
                    break

        for _ in range(9 - len(objects)):
            while True:
                name = targetObject
                while name == targetObject:
                    name = random.choice(list(CAPTCHA_IMGS.keys()))
                img = random.choice(CAPTCHA_IMGS[name])
                if not img in objects:
                    objects.append(img)
                    break
        
        random.shuffle(objects)

        grid = ''
        for object in objects:
            grid += '<img src="data:image/png;base64,' + base64.b64encode(object).decode() + '">'

        return Response(CAPTCHA_PAGE.replace('{{RAY_ID}}', self.ray.getShortID()).replace('{{CAPTCHA_IMGS}}', grid).replace('{{CAPTCHA_TARGET}}', targetObject), 401)