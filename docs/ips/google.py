# uv run -m docs.ips.google

import requests
import json

req = requests.get('https://developers.google.com/search/apis/ipranges/googlebot.json')

ips = []
if req.status_code == 200:
    data = req.json()
    for prefix in data.get('prefixes', []):
        ips.append(prefix.get('ipv4Prefix', prefix.get('ipv6Prefix')))
    with open('resources/googlebot_ips.json', 'w') as f:
        f.seek(0)
        f.write(json.dumps(ips))
else:
    print('Unable to fetch google ips')