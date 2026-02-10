# uv run -m test.script_generator

from app.challenges.full import Script

script = Script()
print(script.code)