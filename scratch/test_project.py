import os
import sqlite3
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

def test_gemini():
    print("--- Testing Gemini ---")
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not found.")
        return
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        # Try a simple generation
        # Using gemini-2.0-flash or gemini-1.5-flash if 2.5 is not found
        model_to_test = "gemini-2.0-flash" 
        response = client.models.generate_content(
            model=model_to_test,
            contents="Hello, respond with 'Gemini OK'"
        )
        print(f"Gemini Response: {response.text}")
    except Exception as e:
        print(f"Gemini Error: {e}")

def test_news_api():
    print("\n--- Testing NewsAPI ---")
    if not NEWS_API_KEY:
        print("NEWS_API_KEY not found.")
        return
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            print("NewsAPI OK")
        else:
            print(f"NewsAPI Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"NewsAPI Exception: {e}")

def test_db():
    print("\n--- Testing Database ---")
    db_path = "memory.db"
    if not os.path.exists(db_path):
        print("memory.db not found.")
        return
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT count(*) FROM memories")
        count = cursor.fetchone()[0]
        print(f"Memories count: {count}")
        
        cursor.execute("SELECT category, key, value FROM memories LIMIT 5")
        for row in cursor.fetchall():
            print(f"  [{row[0]}] {row[1]}: {row[2]}")
            
        cursor.execute("SELECT count(*) FROM conversations")
        conv_count = cursor.fetchone()[0]
        print(f"Conversations count: {conv_count}")
        
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")

if __name__ == "__main__":
    test_gemini()
    test_news_api()
    test_db()
