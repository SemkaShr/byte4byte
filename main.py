from fastapi import FastAPI
import uvicorn
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
    '188.127.241.229', 
    '188.127.241.230', 
    '188.127.241.231', 
    '193.23.199.39', 
    '188.127.241.234',
    '188.127.241.232',
    '188.127.241.233',
    '94.198.55.217'
)

rayGroupDev = RayGroup('dev')
point = Endpoint('captcha.qwertyx.host', 'https://94.198.55.226/', rayGroupDev)
router.addEndpoint(point)

# if __name__ == "__main__":
#     # (threading.Thread(target=test1)).start()
#     uvicorn.run(app, host='127.0.0.1', port=8080, server_header=False, headers=[('server', 'Byte4Byte DDoS Mitigation')], access_log=False)