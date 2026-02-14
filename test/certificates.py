# uv run -m test.certificates

import app.haproxy as haproxy

hap = haproxy.HAProxy(None)
print(hap.check_certificate('new.qwertyx.host'))
print(hap.check_certificate('captcha.qwertyx.host'))
print(hap.check_certificate('systems.qwertyx.host'))
print(hap.check_certificate('uptime.qwertyx.host'))