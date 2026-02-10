from fastapi import FastAPI

import app.haproxy as haproxy
from app.router import Router

import config

logger = config.getLogger('b4b.main')

app = FastAPI()
hap = haproxy.HAProxy(app)
router = Router(app)

# You can configure your app in appConfig file
from appConfig import init
init(hap, router)


# Example appConfig.py:

# from app.endpoint import Endpoint
# from app.ray.group import Group as RayGroup
# from config import SEARCH_SYSTEMS_BOT

# import app.haproxy
# import app.router

# def init(hap: app.haproxy.HAProxy, router: app.router.Router):
#     rayGroup = RayGroup('site')
#     point = Endpoint('domain.example.com', 'https://backend-ip/', rayGroup)
#     rayGroup.whitelistAdd('Some ip or subnet')
#     rayGroup.whitelistAdd(*SEARCH_SYSTEMS_BOT) # Search Systems