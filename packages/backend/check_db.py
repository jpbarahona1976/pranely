import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import os
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
