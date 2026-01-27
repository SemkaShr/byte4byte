import time
import javascript

with open('./app/assets/captcha.js', 'r') as f:
    js = f.read()

obfuscator = javascript.require('../node_modules/javascript-obfuscator/dist/index.js')

timeStart = time.time_ns()
print(obfuscator.obfuscate(js, {
    'renameGlobals': True,
    'compact': True,
    'renameProperties': True,
    'splitStrings': True,
    'numbersToExpressions': True,
    'selfDefending': True
}).getObfuscatedCode())
print('Time elapsed: ', (time.time_ns() - timeStart) / 1000000, 'ms')