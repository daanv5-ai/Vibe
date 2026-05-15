import os
from dotenv import load_dotenv
load_dotenv()
print(f"GEMINI_API_KEY set: {bool(os.environ.get('GEMINI_API_KEY'))}")
print(f"TELEGRAM_BOT_TOKEN set: {bool(os.environ.get('TELEGRAM_BOT_TOKEN'))}")
