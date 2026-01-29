from pathlib import Path
import os
import redis
import javascript

PID = os.getpid()
REDIS = redis.Redis(host='localhost', port=6379, db=0)

RAY_LEN = 256
RAY_LEN_SHORT = 12
RAY_LIFETIME = 1800
RAY_NAME = 'byte4byte.auth'
ASSETS_PATH = Path.cwd() / 'app' / 'assets'
ASSETS_PATH.mkdir(parents=True, exist_ok=True)

FULL_CHALLANGE_SCRIPT = (ASSETS_PATH / 'full_challange.js').read_text()
FULL_CHALLANGE_SCRIPT_AMOUNT = 20
FULL_CHALLANGE_SCRIPT_LIFETIME = 180 # Hint: Do not set less then 90s

OBFUSCATOR_JS = javascript.require('./node_modules/javascript-obfuscator/dist/index.js')

PAGE_503 = (ASSETS_PATH / '503.html').read_text()
PAGE_502 = (ASSETS_PATH / '502.html').read_text()

JA4_KEY_DETECT = '<<BOT>>'
APP_HEADERS = ['x-forwarded-for', 'x-ja4-app', 'x-ja4-raw', 'x-ja4-fingerprint']

BOT_USERAGENT_KEYWORDS = []
BOT_USERAGENT_KEYWORDS.extend([
    'golang', 'wget', 'curl', 'go-http-client', 'apache-httpclient', 'java', 'perl',
    'python', 'openssl', 'headless', 'cypress', 'mechanicalsoup', 'grpc-go', 'okhttp',
    'httpx', 'httpcore', 'aiohttp', 'httputil', 'urllib', 'guzzle', 'axios', 'ruby',
    'zend_http_client', 'wordpress', 'symfony', 'httpclient', 'cpp-httplib', 'ngrok',
    'malware', 'httprequest',
]) # Basic bots
BOT_USERAGENT_KEYWORDS.extend([
    'scan', 'scanner', 'nessus', 'metasploit', 'zgrab', 'zmap', 'nmap', 'research', 'inspect',
]) # Scanners
BOT_USERAGENT_KEYWORDS.extend([
    'bot', 'mastodon', 'https://', 'http://', 'whatsapp', 'twitter', 'facebook', 'chatgpt',
    'telegram', 'crawler', 'colly', 'phpcrawl', 'nutch', 'spider', 'scrapy', 'elinks',
    'imageVacuum', 'apify', 'chrome-lighthouse', 'adsdefender', 'baidu', 'yandex', 'duckduckgo',
    'google', 'yahoo', 'bing', 'microsoftpreview',
]) # Web bots
BOT_USERAGENT_KEYWORDS.extend([
    'mozilla/4.', 'mozilla/3.', 'mozilla/2.', 'fidget-spinner-bot', 'test-bot', 'tiny-bot',
    'download', 'printer', 'router', 'camera', 'phillips hue', 'vpn', 'cisco', 'proxy', 'image',
    'office', 'fetcher', 'feed', 'photon', 'alittle client'
]) # Random bots

BOT_EXCLUDE = ['google', 'yandex'] # Bots to exclude. Only works with User-Agent

import logging
def getLogger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s:     %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger