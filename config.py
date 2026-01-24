from pathlib import Path
from PIL import Image
import os, redis

PID = os.getpid()
REDIS = redis.Redis(host='localhost', port=6379, db=0)

RAY_LEN = 256
RAY_LEN_SHORT = 12
RAY_LIFETIME = 1800
RAY_NAME = 'byte4byte.auth'

CAPTCHA_SIGNATURE_SALT = '02eKPuzlNXhgbyd6ZLaFpk7OVba6k3fU7Nrff3tnX8ONLFaoBB6K156keYuPUTLtq4qUPcWi6dCEtNHqQsRR3qNMY3fojTqS'

PAGES_PATH = Path('app/pages/')
PAGES_PATH.mkdir(parents=True, exist_ok=True)

CAPTCHA_PAGE = (PAGES_PATH / 'captcha.html').read_text()
TIMEOUT_PAGE = (PAGES_PATH / 'timeout.html').read_text()
PAGE_503 = (PAGES_PATH / '503.html').read_text()
PAGE_502 = (PAGES_PATH / '502.html').read_text()

CAPTCHA_IMGS_PATH = Path('captcha_imgs')
CAPTCHA_IMGS_PATH.mkdir(parents=True, exist_ok=True)
CAPTCHA_IMGS = {}

entries = list(CAPTCHA_IMGS_PATH.iterdir())
for entry in entries:
    if entry.is_file() and not entry.suffix == '.tmp':
        name = entry.name.split('.')[0].split('_')[0]
        if not name in CAPTCHA_IMGS:
            CAPTCHA_IMGS[name] = []

        tmpFile = entry.with_suffix('.' + str(PID) + '.tmp')
        
        img = Image.open(entry)
        img = img.resize((128,128))
        img.save(tmpFile, 'JPEG', optimize=True, quality=70)
        CAPTCHA_IMGS[name].append(tmpFile.read_bytes())

        tmpFile.unlink(True)

if len(CAPTCHA_IMGS.keys()) < 2 or len(entries) / len(CAPTCHA_IMGS.keys()) < 4:
    print('You need to have at least 2 captcha objects and 4 images for every')
    exit()

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