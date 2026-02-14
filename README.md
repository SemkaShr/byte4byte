```bash
apt update
apt install nodejs npm haproxy redis postgresql postgresql-contrib
sudo systemctl enable --now postgresql
```
```bash
# Configure Database
sudo -u postgres psql
CREATE ROLE byte4byte_user WITH LOGIN PASSWORD 'YOUR_PASSWORD';
CREATE DATABASE byte4byte OWNER byte4byte_user;
\q
```
```bash
git clone https://github.com/SemkaShr/byte4byte
```
```bash
cd byte4byte
```
```bash
pip install uv
```
```bash
uv sync
```
```bash
npm install --save-dev javascript-obfuscator
```
```bash
# Configure HAProxy config
```
```py
# Configure appConfig.py
from app.endpoint import Endpoint
from app.ray.group import Group as RayGroup
from config import SEARCH_SYSTEMS_BOT

import app.haproxy
import app.router

def init(hap: app.haproxy.HAProxy, router: app.router.Router):
    rayGroup = RayGroup('site')
    point = Endpoint('domain.example.com', 'https://backend-ip/', rayGroup)
    rayGroup.whitelistAdd('ip or subnet')
    rayGroup.whitelistAdd(*SEARCH_SYSTEMS_BOT) 

# Configure dbConfig.py:
DB_NAME = 'byte4byte'
DB_USER = 'byte4byte_user'
DB_PASSWORD = 'YOUR_PASSWORD'
DB_PORT = 5432 
DB_HOST = 'localhost'


```
```bash
./run.sh
```