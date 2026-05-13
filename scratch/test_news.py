import os
from dotenv import load_dotenv
from news_fetcher import fetch_headlines_for_topic, GEOPOLITICAL_TOPICS

load_dotenv()
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

def test_news():
    if not NEWS_API_KEY:
        print("NEWS_API_KEY not found in .env")
        return
    
    # Just test one topic to save credits
    topic = GEOPOLITICAL_TOPICS[0]
    print(f"Fetching headlines for: {topic['label']} (query: {topic['query']})")
    headlines = fetch_headlines_for_topic(NEWS_API_KEY, topic["query"])
    
    if headlines:
        print(f"Found {len(headlines)} headlines:")
        for h in headlines[:3]: # Show first 3
            print(f" - {h}")
    else:
        print("No headlines found (or error occurred).")

if __name__ == "__main__":
    test_news()
