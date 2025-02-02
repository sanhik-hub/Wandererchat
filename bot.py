import os
import logging
import aiohttp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Configuration
TOKEN = ('8066444127:AAFGRH7J21Xry35zo8kPdexmjk8JdPL7S2c')
OPENAI_API_KEY = os.getenv('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')
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
WEBHOOK_URL = os.getenv('RENDER_EXTERNAL_URL')
PORT = int(os.environ.get('PORT', 5000))

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store enabled groups (use database in production)
enabled_groups = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "🤖 Hello! I'm an AI-powered bot powered by ChatGPT.\n"
        "• PM me directly for conversations\n"
        "• Use /enable in groups to activate me (admin only)"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = (
        "🌟 Available Commands:\n"
        "/start - Initial greeting\n"
        "/help - Show this message\n"
        "/enable - Activate bot in groups (admin only)\n"
        "/disable - Deactivate bot in groups (admin only)\n\n"
        "In groups: mention me or reply to my messages!"
    )
    await update.message.reply_text(help_text)

async def enable_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable bot in a group"""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == 'private':
        await update.message.reply_text("❌ This command works in groups only!")
        return

    # Verify admin status
    admins = await context.bot.get_chat_administrators(chat.id)
    if not any(admin.user.id == user.id for admin in admins):
        await update.message.reply_text("🔒 Administrator privileges required!")
        return

    enabled_groups[chat.id] = True
    await update.message.reply_text("✅ Bot activated! Mention me or reply to my messages.")

async def disable_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable bot in a group"""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == 'private':
        await update.message.reply_text("❌ This command works in groups only!")
        return

    # Verify admin status
    admins = await context.bot.get_chat_administrators(chat.id)
    if not any(admin.user.id == user.id for admin in admins):
        await update.message.reply_text("🔒 Administrator privileges required!")
        return

    enabled_groups[chat.id] = False
    await update.message.reply_text("❌ Bot deactivated. Use /enable to reactivate.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming messages"""
    message = update.effective_message
    chat = update.effective_chat
    bot_username = context.bot.username

    # Ignore messages without text
    if not message.text:
        return

    # Handle private chats directly
    if chat.type == 'private':
        response = await generate_chatgpt_response(message.text)
        await message.reply_text(response)
        return

    # Handle group chats when enabled
    if enabled_groups.get(chat.id, False):
        # Check if bot is mentioned or message is a reply to bot
        is_mentioned = f"@{bot_username}" in message.text
        is_reply = message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id
        
        if is_mentioned or is_reply:
            query = message.text.replace(f"@{bot_username}", "").strip()
            if query:
                response = await generate_chatgpt_response(query)
                await message.reply_text(response)

async def generate_chatgpt_response(prompt: str) -> str:
    """Get response from ChatGPT API"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['choices'][0]['message']['content']
                logger.error(f"OpenAI API Error: {response.status} - {await response.text()}")
                return "⚠️ Sorry, I'm having trouble processing that request."
    except Exception as e:
        logger.error(f"Connection Error: {str(e)}")
        return "🔌 Connection error. Please try again later."

def main() -> None:
    """Start the bot"""
    application = Application.builder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("enable", enable_group))
    application.add_handler(CommandHandler("disable", disable_group))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Webhook configuration for Render
    if WEBHOOK_URL:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{WEBHOOK_URL}/webhook",
            allowed_updates=Update.ALL_TYPES
        )
    else:
        # Local polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
