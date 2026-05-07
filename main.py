import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from system_prompt import SYSTEM_PROMPT

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

# Setup Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
generation_config = {
  "temperature": 0.7,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
}

# We initialize a chat model. We can start a chat session to keep history in-memory for now.
# Since we want it per-user, we will store chat sessions in a dict.
user_sessions = {}

def get_chat_session(user_id):
    if user_id not in user_sessions:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=generation_config,
            system_instruction=SYSTEM_PROMPT
        )
        user_sessions[user_id] = model.start_chat(history=[])
    return user_sessions[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="Hey Daan! I'm online. What are we getting done today?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    if not user_text:
        return
        
    # Get or create session
    chat_session = get_chat_session(user_id)
    
    try:
        # Send typing action
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        # Get AI response
        response = chat_session.send_message(user_text)
        
        # Send response back to Telegram
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response.text
        )
    except Exception as e:
        logging.error(f"Error communicating with Gemini: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Oops, I had a brain fart. Something went wrong!"
        )

if __name__ == '__main__':
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token or bot_token == "your_telegram_bot_token_here":
        raise ValueError("No valid TELEGRAM_BOT_TOKEN found in .env")
        
    application = ApplicationBuilder().token(bot_token).build()
    
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    print("Bot is starting...")
    application.run_polling()
