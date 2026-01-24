import app.haproxy as haproxy

hap = haproxy.HAProxy(None)
print(hap.check_certificate('captcha.qwertyx.host'))