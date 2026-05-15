import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from memory import init_db, save_memory, get_memories_as_text

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.5-flash"

async def test_gemini():
    print(f"--- Testing Gemini Connection with {MODEL_NAME} ---")
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found in .env")
        return False
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="Say 'Hello, Daan! Gemini is working.'",
        )
        print(f"Response: {response.text}")
        return "Daan" in response.text
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return False

async def test_memory():
    print("\n--- Testing Memory DB ---")
    init_db()
    user_id = 999999  # Test user
    save_memory(user_id, "preference", "test_key", "test_value")
    memories = get_memories_as_text(user_id)
    print(f"Stored Memories:\n{memories}")
    return "test_key" in memories

async def main():
    gemini_ok = await test_gemini()
    memory_ok = await test_memory()
    
    if gemini_ok and memory_ok:
        print("\nCore logic test passed!")
    else:
        print("\nCore logic test failed.")

if __name__ == "__main__":
    asyncio.run(main())
