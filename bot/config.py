import os
import sys
import django
from pathlib import Path
from dotenv import load_dotenv

# Ensure Django root is in python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
