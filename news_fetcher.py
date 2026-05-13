import os
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2/everything"

# Topics to track with their search queries and emoji labels
GEOPOLITICAL_TOPICS = [
    {"label": "🇺🇦 Ukraine War", "query": "Ukraine war Russia military"},
    {"label": "🕌 Middle East", "query": "Gaza Middle East Israel conflict"},
    {"label": "🚢 Strait of Hormuz", "query": "Strait of Hormuz shipping Iran"},
    {"label": "🤖 AI & Tech", "query": "Artificial Intelligence LLM OpenAI Gemini AI regulation"},
    {"label": "📊 Data Management", "query": "Data governance DAMA DMBOK data steward data management"},
    {"label": "🏦 Banking & Finance", "query": "ABN AMRO banking regulation ECB finance"},
    {"label": "🇳🇱 Dutch Politics", "query": "Netherlands politics Tweede Kamer Mark Rutte Geert Wilders"},
    {"label": "📈 Stocks & Markets", "query": "Tesla stock TSLA NVIDIA AI stocks market news"},
]


def fetch_headlines_for_topic(api_key: str, query: str, max_articles: int = 5) -> list[str]:
    """
    Fetch the latest headlines for a given query from NewsAPI.
    Returns a list of headline strings including source for political context.
    """
    # Only look at the last 24 hours
    from_date = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

    params = {
        "q": query,
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": max_articles,
        "apiKey": api_key,
    }

    try:
        resp = requests.get(NEWSAPI_BASE, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        headlines = []
        for article in articles:
            title = article.get("title", "").strip()
            source = article.get("source", {}).get("name", "Unknown")
            description = article.get("description", "").strip()
            if title and "[Removed]" not in title:
                headlines.append(f"• {title} (Source: {source}) | Details: {description}")
        return headlines
    except Exception as e:
        logger.error("NewsAPI fetch failed for query '%s': %s", query, e)
        return []


def fetch_all_geopolitical_news(api_key: str) -> dict[str, list[str]]:
    """
    Fetch headlines for all tracked topics.
    Returns a dict: { label -> [headlines] }
    """
    results = {}
    for topic in GEOPOLITICAL_TOPICS:
        headlines = fetch_headlines_for_topic(api_key, topic["query"])
        results[topic["label"]] = headlines
    return results


def build_news_context(api_key: str) -> str:
    """
    Build a raw news context string to pass to Gemini for summarization.
    """
    all_news = fetch_all_geopolitical_news(api_key)

    lines = ["Latest news headlines and descriptions (last 24 hours):"]
    any_news = False

    for label, headlines in all_news.items():
        lines.append(f"\n[{label}]")
        if headlines:
            any_news = True
            lines.extend(headlines)
        else:
            lines.append("  • No major headlines in the last 24 hours.")

    if not any_news:
        return ""

    return "\n".join(lines)


def generate_morning_briefing(client, model_name: str, api_key: str, whoop_data: str = "", tasks_data: str = "", calendar_data: str = "") -> str:
    """
    Use Gemini to turn raw headlines, whoop data, tasks, and calendar into a crisp morning briefing for Daan.
    """
    from google.genai import types

    news_context = build_news_context(api_key)

    if not news_context:
        news_context = "No major headlines in the last 24 hours."

    today = datetime.now().strftime("%A, %d %B %Y")

    prompt = f"""You are Daan's structured, casual business planning assistant.
Today is {today}.

WHOOP HEALTH METRICS:
{whoop_data if whoop_data else "No Whoop data available today."}

ACTIVE TASKS:
{tasks_data if tasks_data else "No active tasks in the system."}

TODAY's CALENDAR EVENTS:
{calendar_data if calendar_data else "No calendar events scheduled for today."}

RAW HEADLINES & SOURCES:
{news_context}

YOUR TASK:
Create a highly structured, scannable morning briefing that acts as Daan's control center for the day.

FORMAT RULES:
1. **Health & Readiness**: Start with a very brief summary of his Whoop recovery and sleep. Based on this, give a 1-sentence recommendation on how hard he should push physically today.
2. **Today's Battle Plan**: Review his active tasks, his calendar events, and his recovery. Propose a concrete, prioritized plan of attack for today. Suggest exactly which 2-3 tasks he should focus on and mention when they fit around his meetings/events. Keep it actionable and business-like.
3. **World Context**: For EACH news category (Ukraine, Middle East, Hormuz, AI, Data, Banking, Dutch Politics, Stocks):
   - Provide a 1-sentence punchy summary.
   - Mention the source and its general political leaning.
   - Follow with a concise "In-depth Analysis" (2-3 sentences) on why this matters.
   - For the Strait of Hormuz: Explicitly state "STATUS: OPEN" or "STATUS: RESTRICTED/CLOSED".
4. Tone: Casual, structured, analytical. Occasional light wit, but mostly a focused business planner. No fluff. Use emojis for structure.

Keep it scannable with clear headings.
"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1500,
            ),
        )
        return response.text
    except Exception as e:
        logger.error("Gemini briefing generation failed: %s", e)
        return "Morning Daan! 🌅 I have the news but my summary engine is sulking. Try again in a bit."

