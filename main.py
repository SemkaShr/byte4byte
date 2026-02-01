from fastapi import FastAPI

import app.haproxy as haproxy
from app.router import Router
from app.endpoint import Endpoint
from app.ray.group import Group as RayGroup

import config

logger = config.getLogger('b4b.main')

app = FastAPI()
hap = haproxy.HAProxy(app)
router = Router(app)

rayGroup = RayGroup('qwertyx')
point = Endpoint('new.qwertyx.host', 'https://94.198.55.226/', rayGroup)
router.addEndpoint(point)
point = Endpoint('control.qwertyx.host', 'https://94.198.55.226/', rayGroup)
router.addEndpoint(point)
point = Endpoint('my.qwertyx.host', 'https://94.198.55.226/', rayGroup)
router.addEndpoint(point)
point = Endpoint('qwertyx.host', 'https://94.198.55.226/', rayGroup)
router.addEndpoint(point)
point = Endpoint('uptime.qwertyx.host', 'https://94.198.55.226/', rayGroup)
router.addEndpoint(point)
point = Endpoint('systems.qwertyx.host', 'https://94.198.55.226/', rayGroup)
router.addEndpoint(point)

rayGroup.whitelistAdd(
    '88.147.152.98', '146.185.240.196', '78.111.155.219', # Normal user, but blocked
    '188.127.241.229', 
    '188.127.241.230', 
    '188.127.241.231',
    '188.127.241.235', 
    '193.23.199.39', 
    '188.127.241.234',
    '188.127.241.232',
    '188.127.241.233',
    '94.198.55.217',
    '193.176.92.70', # PAYANYWAY
    '31.133.220.8', # HELEKET
    '3.18.12.63', # STRIPE
    '3.130.192.231', # STRIPE
    '13.235.14.237', # STRIPE
    '13.235.122.149', # STRIPE
    '18.211.135.69', # STRIPE
    '35.154.171.200', # STRIPE
    '52.15.183.38', # STRIPE
    '54.88.130.119', # STRIPE
    '54.88.130.237', # STRIPE
    '54.187.174.169', # STRIPE
    '54.187.205.235', # STRIPE
    '54.187.216.72' # STRIPE
)

rayGroup.whitelistAdd(*config.SEARCH_SYSTEMS_BOT) # Search Systems

rayGroupDev = RayGroup('dev')
point = Endpoint('captcha.qwertyx.host', 'https://94.198.55.226/', rayGroupDev)
router.addEndpoint(point)
