import hashlib
import time
import base64
import json
import string
import random

from config import OBFUSCATOR_JS
from Crypto.Cipher import AES

class Script:
    def __init__(self):
        self.code = None
        self.rawCode = None
        self.varNames = None
        
    def load(self, key, data):
        if len(key) != 32:
            return False
        self.encryptionKey = key
        self.filename = self.getScriptFilename()
        self.endpoint = self.getScriptEndpoint()
        
        self.code = data.get('code', None)
        self.varNames = data.get('vars', None)
        
        return self
    
    def decrypt(self, data):
        encrypted = base64.b64decode(data)
    
        cipher = AES.new(
            self.encryptionKey.encode()[:32], 
            AES.MODE_CBC, 
            iv=bytes(16)
        )

        decrypted = cipher.decrypt(encrypted)
        padding_length = decrypted[-1]
        decrypted = decrypted[:-padding_length]
        
        return json.loads(decrypted.decode())

            
    def dump(self):
        return {
            'code': self.code,
            'vars': self.varNames
        }
        
    def getCode(self):
        if self.code == None:
            self.varNames = self.getNames()
        
            for i, key in enumerate(self.VARIABLES):
                self.rawCode = self.rawCode.replace('{{' + str(key) + '}}', self.varNames[i])
                
            self.rawCode = self.rawCode.replace('{{SCRIPT_ENDPOINT}}', self.endpoint)
            self.rawCode = self.rawCode.replace('{{SCRIPT_KEY}}', self.encryptionKey)
            
            self.code = OBFUSCATOR_JS.obfuscate(self.rawCode, {
                'renameGlobals': True,
                'compact': True,
                'renameProperties': False,
                'splitStrings': False,
                'numbersToExpressions': True,
                'transformObjectKeys': False,
                'reservedNames': ['iv', 'Uint8Array'],
                'selfDefending': True
            }).getObfuscatedCode()
        return self.code
        
    def save(self):
        pass
    
    def generate(self, seed=time.time_ns()):
        self.encryptionKey = self.getString(seed, 32)
        self.filename = self.getScriptFilename()
        self.endpoint = self.getScriptEndpoint()
        self.rawCode = self.getRawCode()
        self.code = self.getCode()
        self.save()
        return self
    
    def getRawCode(self):
        pass
    
    def get(self, key):
        if self.varNames == None:
            return None
        return self.varNames[self.VARIABLES.index(key)]
    
    def getNames(self):
        varLen = max(len(self.VARIABLES) // len(string.ascii_letters), 1)
        names = []
        for i in range(len(self.VARIABLES)):
            name = ''
            n = i
            for _ in range(varLen):
                n, idx = divmod(n, len(string.ascii_letters))
                name += string.ascii_letters[idx]
            names.append(name)
            
        random.seed(self.encryptionKey)
        random.shuffle(names)
            
        return names
    
    def getScriptEndpoint(self):
        return '/' + self.getString(hashlib.sha256(self.encryptionKey.encode()).hexdigest(), 32)
    
    def getScriptFilename(self):
        return self.getString(self.encryptionKey, 32) + '.js'
    
    def getString(self, seed, length):
        random.seed(seed)
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))