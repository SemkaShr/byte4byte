# uv run -m test.script_generator

from app.challanges.full import Script

script = Script()
print(script.code)