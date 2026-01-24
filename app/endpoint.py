import config
import time
from enum import Enum
from app.ray.group import Group as RayGroup
from app.ray.ray import Ray, Status

class Endpoint:
    def __init__(self, host: str, endpointAddress: str, rayGroup: RayGroup):
        self.host = host
        self.address = endpointAddress
        self.rayGroup = rayGroup

    async def handleRequest(self, request):
        ray = self.rayGroup.getRay(request)

        while True:
            if not ray.verify() in [Status.UNVERFIED, Status.VERIFING]:
                break
            time.sleep(0.1)
    
        return EndpointResponse(ray, EndpointResponseStatus(ray.status.value))
    
    def getAddress(self) -> str:
        return self.address

class EndpointResponse:
    def __init__(self, ray, status):
        self.ray = ray
        self.status = status

class EndpointResponseStatus(Enum):
    VERFIED = 'verfied'
    CAPTCHA = 'captcha'
    BLOCKED = 'blocked'