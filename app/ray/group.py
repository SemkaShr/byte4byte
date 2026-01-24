from config import RAY_NAME, RAY_LEN, REDIS, RAY_LIFETIME, getLogger

import random
import string
import time
import json

from enum import Enum

from app.ray.ray import Ray

class Group:
    def __init__(self, name : str):
        self.name = name
        self.logger = getLogger('b4b.' + name + '.group')

    def getRay(self, request):
        rayID = request.cookies.get(RAY_NAME)
        if rayID is not None and REDIS.exists('ray:' + self.name + ':' + str(rayID)):
            ray = Ray(self, rayID, request)
            ray.load(json.loads(REDIS.get('ray:' + self.name + ':' + str(rayID))))
        else:
            ray = Ray(self, self._genRayID(), request)
            ray.save()
        return ray

    def _genRayID(self):
        random.seed(time.time_ns())
        while True:
            id = (''.join(random.choice(string.ascii_letters + string.digits) for _ in range(RAY_LEN))) + '.' + str(time.time_ns())
            if REDIS.exists('ray:' + self.name + ':' + id) == 0:
                break
        return id