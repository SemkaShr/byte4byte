# uv run -m test.redis

from config import REDIS

# REDIS.set('test', 'test', 10)
# print(REDIS.ttl('test'))
# REDIS.set('test', 'test', 15)
# print(REDIS.ttl('test'))

print(REDIS.keys('ray:dev:*'))