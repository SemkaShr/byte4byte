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