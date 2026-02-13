
import subprocess
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse
from pathlib import Path
import config

from pyhaproxy.parse import Parser
from pyhaproxy.render import Render
import pyhaproxy.config as hapconfig

TMP_PATH = './tmp/certbot/'
CHALLENGE_PATH = Path(TMP_PATH) / ".well-known" / "acme-challenge"
CHALLENGE_PATH.mkdir(parents=True, exist_ok=True)

HAPROXY_PATH = '/etc/haproxy/'
HAPROXY_FILENAME = HAPROXY_PATH + 'haproxy.cfg'
HAPROXY_CERT_PATH = HAPROXY_PATH + 'certs/'
Path(HAPROXY_CERT_PATH).mkdir(parents=True, exist_ok=True)

class HAProxy:
    def __init__(self, app = None):
        self.cfg_parser = Parser(HAPROXY_FILENAME)
        self.configuration = self.cfg_parser.build_configuration()
        self.logger = config.getLogger('b4b.haproxy')

        if app is not None:
            @app.get("/.well-known/acme-challenge/{token}", response_class=PlainTextResponse)
            async def serve_challenge(token: str):
                file_path = CHALLENGE_PATH / token
                if file_path.exists():
                    return file_path.read_text()
                raise HTTPException(status_code=404, detail="Challenge not found")
    
    def check_certificate(self, domain: str):
        if self.certificate_exists(domain):
            return True
        else:
            result = self.issue_certificate(domain)
            if result['success']:
                fullchain = subprocess.run([
                    'sudo', 'cat', result['cert_path']
                ], capture_output=True, text=True, check=True)
                
                privkey = subprocess.run([
                    'sudo', 'cat', result['key_path']
                ], capture_output=True, text=True, check=True)
                
                with open(HAPROXY_CERT_PATH + domain + '.pem', 'w') as f:
                    f.seek(0)
                    f.write(fullchain.stdout)
                    f.write(privkey.stdout)
                
                self.logger.info(f'Created certificate for {domain}')
                return True
            else:
                self.logger.warning(f'Unable to generate certificate for {domain}. ' + result['stderr'])

    def certificate_exists(self, domain: str):
        return (Path(HAPROXY_CERT_PATH) / (domain + '.pem')).exists()

    def issue_certificate(self, domain: str, email: str = 'admin@swapl.io'):
        http_in = self.configuration.frontend('http_in')
        http_in.remove_config('redirect', 'scheme https code 301 if !certbot_challenge')
        http_in.remove_config('redirect', 'scheme https code 301')
        http_in.remove_usebackend('b4b_main')

        for acl in http_in.acls():
            if acl.value == 'hdr(host) -i ' + domain:
                http_in.config_block.remove(acl)

        http_in.add_acl(hapconfig.Acl('certbot_challenge', 'hdr(host) -i ' + domain))

        http_in.add_usebackend(hapconfig.UseBackend('b4b_main', 'if', 'certbot_challenge', False))
        http_in.add_config(hapconfig.Config('redirect', 'scheme https code 301 if !certbot_challenge'))

        if not self.save_configuration():
            return {'success': False}

        cmd = [
            "sudo", "certbot", "certonly",
            "--non-interactive",
            "--agree-tos",
            "--email", email,
            "--webroot",
            "-w", TMP_PATH,
            "-d", domain,
            "-v"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        for acl in http_in.acls():
            if acl.value == 'hdr(host) -i ' + domain:
                http_in.config_block.remove(acl)

        if len(http_in.acls()) == 0:
            http_in.remove_usebackend('b4b_main')
            http_in.remove_config('redirect', 'scheme https code 301 if !certbot_challenge')
            http_in.add_config(hapconfig.Config('redirect', 'scheme https code 301'))
        
        if not self.save_configuration():
            return {'success': False}

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
            "cert_path": f"/etc/letsencrypt/live/{domain}/fullchain.pem",
            "key_path": f"/etc/letsencrypt/live/{domain}/privkey.pem",
        }
    
    def save_configuration(self):
        cfg_render = Render(self.configuration)
        cfg_render.dumps_to(HAPROXY_FILENAME + '.new')

        result = subprocess.run(
            ['haproxy', '-c', '-f', HAPROXY_FILENAME + '.new'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            subprocess.run(['cp', HAPROXY_FILENAME, HAPROXY_FILENAME + '.old'], check=True)
            subprocess.run(['cp', HAPROXY_FILENAME + '.new', HAPROXY_FILENAME], check=True)
            subprocess.run(['rm', HAPROXY_FILENAME + '.new'], check=True)
            subprocess.run(['systemctl', 'reload', 'haproxy'], check=True)

            self.logger.info('Updated HAProxy configuration and reloaded')
            return True
        else:
            self.logger.error('Configuration is invalid. ' + result.stderr)
            return False