from config import RAY_NAME, RAY_LEN, REDIS, getLogger

import random
import string
import time
import json
import ipaddress

from app.ray.ray import Ray

class Group:
    def __init__(self, name : str):
        self.name = name
        self.logger = getLogger('b4b.group.' + name)
        self.whitelist = []
        
    def whitelistAdd(self, *subnets):
        for subnet_str in subnets:
            if '/' in subnet_str:
                subnet = ipaddress.ip_network(subnet_str, strict=False)
            else:
                subnet = ipaddress.ip_network(f"{subnet_str}/{'128' if ipaddress.ip_address(subnet_str).version == 6 else '32'}", strict=False)
            self.whitelist.append(subnet)

    def getRay(self, request):
        rayID = request.cookies.get(RAY_NAME)
        if rayID is not None and REDIS.exists('ray:' + self.name + ':' + str(rayID)):
            ray = Ray(self, rayID, request)
            ray.load(json.loads(REDIS.get('ray:' + self.name + ':' + str(rayID))))
        else:
            ray = Ray(self, self._genRayID(), request)
            ray.save(False)
        return ray

    def _genRayID(self):
        random.seed(time.time_ns())
        while True:
            id = (''.join(random.choice(string.ascii_letters + string.digits) for _ in range(RAY_LEN))) + '.' + str(time.time_ns())
            if REDIS.exists('ray:' + self.name + ':' + id) == 0:
                break
        return id