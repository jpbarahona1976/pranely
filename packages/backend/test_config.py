import os
os.chdir(r'C:\Projects\Pranely\packages\backend')
from app.core.config import get_settings
s = get_settings()
print("DATABASE_URL:", s.DATABASE_URL)
print("ENV:", s.ENV)
print("DEBUG:", s.DEBUG)