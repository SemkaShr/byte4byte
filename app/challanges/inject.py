import random
import time
import string

class InjectChallange:
    def __init__(self, ray):
        self.ray = ray
        
    def getInjectCode(self):
        return ' '.encode()
    
    def getScriptCode(self):
        return 'alert("Hello, World!")'
    
    def getScriptFilename(self):
        return self.getString(self.ray.id + str(self.ray.createTime), 32) + '.js'
    
    def getString(self, seed, length):
        random.seed(seed)
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))