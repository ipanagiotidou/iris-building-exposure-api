
from app.core.config import settings

print("Loading settings from .env file...")

print("Application:", settings.app_name)
print("Environment:", settings.app_env)
print("Debug mode:", settings.debug)