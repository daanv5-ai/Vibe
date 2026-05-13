import os
import logging
import pytz
from datetime import datetime, time as dt_time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

from system_prompt import SYSTEM_PROMPT
from memory import (
    init_db,
    save_memory,
    get_memories,
    get_memories_as_text,
    delete_memory,
    clear_all_memories,
    save_conversation_turn,
    get_recent_conversation,
)
from news_fetcher import generate_morning_briefing
import tasks
from whoop_manager import get_whoop_data

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
_raw_chat_id = os.environ.get("DAAN_CHAT_ID", "")
DAAN_CHAT_ID = int(_raw_chat_id) if _raw_chat_id.lstrip("-").isdigit() else 0

AMSTERDAM_TZ = pytz.timezone("Europe/Amsterdam")
MODEL_NAME = "gemini-2.5-flash"

# ─── Gemini Setup (new google.genai SDK) ──────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)

# Per-user conversation history stored as list of Content dicts
# { user_id: [ {"role": ..., "parts": [{"text": ...}]}, ... ] }
user_histories: dict[int, list] = {}


def _build_system_prompt_for_user(user_id: int) -> str:
    """Build the full system prompt including injected long-term memories and current time."""
    memory_block = get_memories_as_text(user_id)
    prompt = SYSTEM_PROMPT
    if memory_block:
        prompt += f"\n\n{memory_block}"
    
    # Add calendar context (current time is crucial for booking)
    now = datetime.now(AMSTERDAM_TZ)
    prompt += f"\n\n## Contextual Info\nCurrent Time: {now.strftime('%A, %B %d, %Y at %H:%M:%S')} (Amsterdam time)"
    return prompt


def _get_history(user_id: int) -> list:
    """Get or initialise conversation history from DB."""
    if user_id not in user_histories:
        recent = get_recent_conversation(user_id, limit=20)
        user_histories[user_id] = [
            types.Content(
                role=turn["role"],
                parts=[types.Part(text=turn["content"])]
            )
            for turn in recent
        ]
        logger.info("Loaded %d history turns for user %s", len(user_histories[user_id]), user_id)
    return user_histories[user_id]


from calendar_manager import list_upcoming_events, add_calendar_event

async def _chat(user_id: int, user_parts: list[types.Part]) -> str:
    """Send a message and handle any tool calls (Function Calling)."""
    history = _get_history(user_id)
    system_prompt = _build_system_prompt_for_user(user_id)

    # Append the new user turn
    history.append(types.Content(role="user", parts=user_parts))

    # We use a loop to handle potential multiple tool calls or follow-ups
    while True:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[types.Tool(function_declarations=[
                    types.FunctionDeclaration(
                        name="list_upcoming_events",
                        description="List the user's upcoming calendar events.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "max_results": {"type": "INTEGER", "description": "Number of events to show."}
                            }
                        }
                    ),
                    types.FunctionDeclaration(
                        name="add_calendar_event",
                        description="Add a new event to the user's Google Calendar.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "summary": {"type": "STRING", "description": "Short title of the event."},
                                "start_time_iso": {"type": "STRING", "description": "ISO 8601 start time (e.g. 2025-05-07T19:00:00)."},
                                "end_time_iso": {"type": "STRING", "description": "Optional ISO 8601 end time."},
                                "description": {"type": "STRING", "description": "Optional details about the event."},
                                "location": {"type": "STRING", "description": "Optional location."}
                            },
                            "required": ["summary", "start_time_iso"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="add_task",
                        description="Add a new task or project step to the user's to-do list.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "title": {"type": "STRING", "description": "The specific task to be done."},
                                "project_name": {"type": "STRING", "description": "Optional project name this task belongs to."}
                            },
                            "required": ["title"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="list_tasks",
                        description="List the user's active tasks or projects.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "status": {"type": "STRING", "description": "Filter by status: 'pending', 'completed', or 'all'. Defaults to 'pending'."},
                                "project_name": {"type": "STRING", "description": "Filter by a specific project name."}
                            }
                        }
                    ),
                    types.FunctionDeclaration(
                        name="update_task_status",
                        description="Update the status of a specific task (e.g. mark it as completed).",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "task_id": {"type": "INTEGER", "description": "The ID of the task to update."},
                                "status": {"type": "STRING", "description": "The new status: 'pending' or 'completed'."}
                            },
                            "required": ["task_id", "status"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="get_whoop_data",
                        description="Fetch the user's latest Whoop metrics (Recovery, Strain, Sleep). Use this to inform scheduling or fitness advice.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {}
                        }
                    )
                ])],
                temperature=0.7,
            ),
        )

        # Check for function calls
        content = response.candidates[0].content
        history.append(content) # Add model turn to history

        tool_calls = [p.function_call for p in content.parts if p.function_call]
        if not tool_calls:
            return response.text

        # Execute tool calls
        tool_responses = []
        for call in tool_calls:
            logger.info("Bot calling function: %s with args %s", call.name, call.args)
            if call.name == "list_upcoming_events":
                result = list_upcoming_events(**call.args)
            elif call.name == "add_calendar_event":
                result = add_calendar_event(**call.args)
            elif call.name == "add_task":
                result = tasks.add_task(user_id=user_id, **call.args)
            elif call.name == "list_tasks":
                result = tasks.list_tasks(user_id=user_id, **call.args)
            elif call.name == "update_task_status":
                result = tasks.update_task_status(user_id=user_id, **call.args)
            elif call.name == "get_whoop_data":
                result = get_whoop_data()
            else:
                result = f"Error: Tool {call.name} not found."
            
            tool_responses.append(types.Part(
                function_response=types.FunctionResponse(
                    name=call.name,
                    response={"result": result}
                )
            ))
        
        # Add tool responses to history and loop back for Gemini to generate final text
        history.append(types.Content(role="tool", parts=tool_responses))


async def _one_shot(prompt: str) -> str:
    """Single stateless Gemini call for utility tasks like memory extraction."""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=512,
        ),
    )
    return response.text.strip()


# ─── Memory Extraction ────────────────────────────────────────────────────────

async def _try_extract_memory(user_id: int, user_text: str, bot_reply: str):
    """Lightweight pass to detect if anything in this exchange is worth storing long-term."""
    extraction_prompt = f"""You are a memory extraction system for a personal AI assistant.

Given this exchange, identify ONLY genuinely new, persistent facts about the user worth storing long-term.
Do NOT extract things that are temporary, conversational filler, or already obvious from context.

User said: "{user_text}"
Assistant replied: "{bot_reply}"

If there is something worth remembering, respond in EXACTLY this format (one per line):
MEMORY|<category>|<key>|<value>

category must be one of: fact, preference, goal, note
If nothing is worth storing, respond with: NONE

Examples of good memories:
MEMORY|goal|fitness_goal|Wants to run a 10k by September
MEMORY|preference|communication_style|Prefers very short bullet-point responses
MEMORY|fact|new_project|Started building a Telegram bot with AI features in May 2025

Examples of bad memories (skip these):
- "User said hello"
- "User asked about the weather"  
- "User seems tired today"
"""
    try:
        text = await _one_shot(extraction_prompt)
        if text == "NONE" or not text:
            return
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("MEMORY|"):
                parts = line.split("|")
                if len(parts) >= 4:
                    _, category, key, value = parts[0], parts[1], parts[2], "|".join(parts[3:])
                    save_memory(user_id, category, key, value)
    except Exception as e:
        logger.warning("Memory extraction failed: %s", e)


# ─── Telegram Command Handlers ────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hey Daan! 👋 I'm back online. What are we conquering today?",
    )


async def handle_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger the morning briefing."""
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    if not NEWS_API_KEY or NEWS_API_KEY == "your_newsapi_key_here":
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ *NEWS\_API\_KEY not set* — I can't fetch the news without it\!\n"
                "Get a free key at https://newsapi.org and add it to your \.env file\."
            ),
            parse_mode="MarkdownV2",
        )
        return

    briefing = generate_morning_briefing(client, MODEL_NAME, NEWS_API_KEY)
    await context.bot.send_message(chat_id=chat_id, text=briefing)


async def handle_memory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all stored long-term memories."""
    user_id = update.effective_user.id
    memories = get_memories(user_id)

    if not memories:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🧠 No long-term memories stored yet. Keep chatting and I'll start picking things up!",
        )
        return

    lines = ["🧠 *Here's what I remember about you:*\n"]
    grouped: dict[str, list[str]] = {}
    for m in memories:
        grouped.setdefault(m["category"], []).append(f"  • *{m['key']}*: {m['value']}")

    for category, items in grouped.items():
        lines.append(f"*{category.capitalize()}s:*")
        lines.extend(items)
        lines.append("")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="\n".join(lines),
        parse_mode="Markdown",
    )


async def handle_forget_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/forget <key> — delete a specific memory."""
    user_id = update.effective_user.id
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage: `/forget <key>`\nExample: `/forget fitness_goal`\n\nUse /memory to see all keys.",
            parse_mode="Markdown",
        )
        return

    key = " ".join(context.args)
    deleted = delete_memory(user_id, key)
    msg = f"🗑️ Done — forgotten `{key}`." if deleted else f"🤔 No memory found for `{key}`. Check /memory."
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown"
    )


async def handle_clearmemory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wipe all long-term memories and reset the session."""
    user_id = update.effective_user.id
    clear_all_memories(user_id)
    user_histories.pop(user_id, None)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🧹 Done. Wiped everything. Fresh start.",
    )


async def handle_calendar_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually list upcoming events."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    events = list_upcoming_events()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=events, parse_mode="Markdown")


# ─── Main Message Handler ─────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text or update.message.caption or ""
    
    if not update.message.text and not update.message.photo:
        return

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        user_parts = []
        if user_text:
            user_parts.append(types.Part(text=user_text))
            
        if update.message.photo:
            # Use the largest available photo
            photo = await update.message.photo[-1].get_file()
            photo_bytes = await photo.download_as_bytearray()
            user_parts.append(types.Part.from_bytes(data=bytes(photo_bytes), mime_type="image/jpeg"))
            logger.info("Received photo from user %s", user_id)

        reply = await _chat(user_id, user_parts)

        await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

        # Persist to DB
        # Store a placeholder for the image in the conversation DB
        display_text = user_text + " [Photo]" if update.message.photo else user_text
        save_conversation_turn(user_id, "user", display_text)
        save_conversation_turn(user_id, "model", reply)

        # Background memory extraction (Gemini will use its 'vision' of the reply to extract facts)
        await _try_extract_memory(user_id, display_text, reply)

    except Exception as e:
        logger.error("Error in handle_message: %s", e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Oops, something broke on my end. Try again in a sec!",
        )


# ─── Scheduled Morning Briefing ───────────────────────────────────────────────

async def send_morning_briefing(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled job at 07:00 Amsterdam time."""
    if not DAAN_CHAT_ID:
        logger.warning("DAAN_CHAT_ID not set — skipping morning briefing")
        return

    if not NEWS_API_KEY or NEWS_API_KEY == "your_newsapi_key_here":
        await context.bot.send_message(
            chat_id=DAAN_CHAT_ID,
            text="Good morning Daan! 🌅 I'd love to give you the geo-briefing but NEWS_API_KEY isn't configured.",
        )
        return

    logger.info("Sending morning briefing to chat_id=%s", DAAN_CHAT_ID)
    
    whoop_data = get_whoop_data()
    tasks_data = tasks.list_tasks(DAAN_CHAT_ID)
    calendar_data = list_upcoming_events(max_results=5)
    
    briefing = generate_morning_briefing(
        client, 
        MODEL_NAME, 
        NEWS_API_KEY, 
        whoop_data=whoop_data, 
        tasks_data=tasks_data,
        calendar_data=calendar_data
    )
    await context.bot.send_message(chat_id=DAAN_CHAT_ID, text=briefing)


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        raise ValueError("No valid TELEGRAM_BOT_TOKEN found in .env")

    init_db()
    tasks.init_db()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("briefing", handle_briefing))
    application.add_handler(CommandHandler("memory", handle_memory_cmd))
    application.add_handler(CommandHandler("forget", handle_forget_cmd))
    application.add_handler(CommandHandler("clearmemory", handle_clearmemory_cmd))
    application.add_handler(CommandHandler("calendar", handle_calendar_list))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO & (~filters.COMMAND), handle_message))

    job_queue = application.job_queue
    if job_queue is not None:
        # The regular daily job
        job_queue.run_daily(
            send_morning_briefing,
            time=dt_time(hour=7, minute=0, second=0, tzinfo=AMSTERDAM_TZ),
            name="morning_briefing",
        )
        
        # ONE-TIME TEST JOB for 18:10 today
        test_time = dt_time(hour=18, minute=10, second=0, tzinfo=AMSTERDAM_TZ)
        job_queue.run_once(send_morning_briefing, when=test_time, name="test_briefing")
        
        logger.info("Morning briefing scheduled at 07:00 Europe/Amsterdam")
        logger.info("TEST briefing scheduled for 18:10:00 Europe/Amsterdam")
    else:
        logger.warning("JobQueue not available — install APScheduler for scheduled briefings.")

    print("Bot is online. Memory active. Morning briefing scheduled at 07:00 AMS.")
    application.run_polling()
