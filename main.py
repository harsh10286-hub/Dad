import os
import asyncio
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from scraper import create_scraper
from otp_filter import otp_filter
from utils import format_otp_message, format_multiple_otps, get_status_message
import threading
import time

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')
IVASMS_EMAIL = os.getenv('IVASMS_EMAIL')
IVASMS_PASSWORD = os.getenv('IVASMS_PASSWORD')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))
CHANNEL_URL = os.getenv('CHANNEL_URL', 'https://t.me/StormNumberChannel')

bot_stats = {
    'start_time': datetime.now(),
    'total_otps_sent': 0,
    'last_check': 'Never',
    'last_error': None,
    'is_running': False
}

bot_instance: Bot = None
scraper = None
_bot_loop: asyncio.AbstractEventLoop = None


def is_owner(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == OWNER_ID


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await update.message.reply_text(
        "🤖 <b>Telegram OTP Bot</b>\n\n"
        "🎯 <b>Commands:</b>\n"
        "/start - This message\n"
        "/status - Bot status\n"
        "/check - Manual OTP check\n"
        "/test - Send test OTP\n"
        "/stats - Detailed stats",
        parse_mode='HTML'
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    uptime = str(datetime.now() - bot_stats['start_time']).split('.')[0]
    cache_stats = otp_filter.get_cache_stats()
    await update.message.reply_text(
        get_status_message({
            'uptime': uptime,
            'total_otps_sent': bot_stats['total_otps_sent'],
            'last_check': bot_stats['last_check'],
            'cache_size': cache_stats['total_cached'],
            'monitor_running': bot_stats['is_running']
        }),
        parse_mode='HTML'
    )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await update.message.reply_text("🔍 <b>Checking for new OTPs...</b>", parse_mode='HTML')
    await asyncio.get_event_loop().run_in_executor(None, check_and_send_otps)
    await update.message.reply_text(
        f"✅ <b>Done!</b>\nLast check: {bot_stats['last_check']}\nTotal sent: {bot_stats['total_otps_sent']}",
        parse_mode='HTML'
    )


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    test_otp = {
        'otp': '123456',
        'phone': '+917446400377',
        'service': 'Test Service',
    }
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=CHANNEL_URL)]])
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=format_otp_message(test_otp),
        parse_mode='HTML',
        reply_markup=keyboard
    )
    await update.message.reply_text("✅ <b>Test message sent!</b>", parse_mode='HTML')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    uptime = str(datetime.now() - bot_stats['start_time']).split('.')[0]
    cache_stats = otp_filter.get_cache_stats()
    await update.message.reply_text(
        f"📊 <b>Bot Statistics</b>\n\n"
        f"⏱️ Uptime: {uptime}\n"
        f"📨 OTPs Sent: {bot_stats['total_otps_sent']}\n"
        f"🔍 Last Check: {bot_stats['last_check']}\n"
        f"💾 Cache Size: {cache_stats['total_cached']} items\n"
        f"🔧 Status: {'🟢 Running' if bot_stats['is_running'] else '🔴 Stopped'}\n"
        f"❌ Last Error: {bot_stats['last_error'] or 'None'}",
        parse_mode='HTML'
    )


def send_otp_to_owner(message: str):
    """Thread-safe send to owner — schedules on the bot's event loop."""
    if not bot_instance or not OWNER_ID or not _bot_loop:
        logger.error("Bot not ready to send messages")
        return False
    try:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=CHANNEL_URL)]])
        future = asyncio.run_coroutine_threadsafe(
            bot_instance.send_message(
                chat_id=OWNER_ID,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard
            ),
            _bot_loop
        )
        future.result(timeout=15)
        logger.info("Message sent to owner")
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        bot_stats['last_error'] = str(e)
        return False


def check_and_send_otps():
    global bot_stats
    try:
        if not scraper:
            logger.warning("Scraper not initialized — skipping check")
            return
        logger.info("Checking for new OTPs...")
        messages = scraper.fetch_messages()
        bot_stats['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not messages:
            logger.info("No messages found")
            return

        new_messages = otp_filter.filter_new_otps(messages)
        if not new_messages:
            logger.info("No new OTPs (all duplicates)")
            return

        logger.info(f"Found {len(new_messages)} new OTPs")
        for otp_data in new_messages:
            if send_otp_to_owner(format_otp_message(otp_data)):
                bot_stats['total_otps_sent'] += 1
    except Exception as e:
        logger.error(f"Error in check_and_send_otps: {e}")
        bot_stats['last_error'] = str(e)


def background_monitor():
    bot_stats['is_running'] = True
    logger.info("Background OTP monitor started (60s interval)")
    while bot_stats['is_running']:
        try:
            check_and_send_otps()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(120)


def run_flask():
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Flask health server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


@app.route('/')
def home():
    uptime = str(datetime.now() - bot_stats['start_time']).split('.')[0]
    return jsonify({
        'status': 'running',
        'uptime': uptime,
        'total_otps_sent': bot_stats['total_otps_sent'],
        'last_check': bot_stats['last_check'],
        'last_error': bot_stats['last_error'],
        'monitor_running': bot_stats['is_running']
    })


@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200


@app.route('/check-otp')
def manual_check():
    try:
        check_and_send_otps()
        return jsonify({'status': 'success', 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/status')
def bot_status():
    uptime = str(datetime.now() - bot_stats['start_time']).split('.')[0]
    cache_stats = otp_filter.get_cache_stats()
    return jsonify({
        'uptime': uptime,
        'total_otps_sent': bot_stats['total_otps_sent'],
        'last_check': bot_stats['last_check'],
        'cache_size': cache_stats['total_cached'],
        'monitor_running': bot_stats['is_running']
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({'status': 'error', 'message': 'Not found'}), 404


async def main():
    global bot_instance, scraper, _bot_loop

    logger.info("=== Starting Telegram OTP Bot ===")

    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    if not OWNER_ID:
        raise ValueError("OWNER_ID is not set")

    _bot_loop = asyncio.get_running_loop()

    scraper = create_scraper(IVASMS_EMAIL, IVASMS_PASSWORD)
    if not scraper:
        logger.error("IVASMS scraper could not be created — check IVASMS_EMAIL and IVASMS_PASSWORD")

    telegram_app = Application.builder().token(BOT_TOKEN).build()
    bot_instance = telegram_app.bot

    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("status", status_command))
    telegram_app.add_handler(CommandHandler("check", check_command))
    telegram_app.add_handler(CommandHandler("test", test_command))
    telegram_app.add_handler(CommandHandler("stats", stats_command))

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    monitor_thread = threading.Thread(target=background_monitor, daemon=True)
    monitor_thread.start()

    logger.info("Starting Telegram polling...")
    async with telegram_app:
        await telegram_app.start()
        await telegram_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Bot is online and polling for commands")

        try:
            await bot_instance.send_message(
                chat_id=OWNER_ID,
                text=(
                    "🚀 <b>Bot Started!</b>\n\n"
                    "✅ Telegram connected\n"
                    f"{'✅' if scraper else '⚠️'} IVASMS scraper {'ready' if scraper else 'failed — check credentials'}\n"
                    "🔍 Monitoring every 60 seconds\n\n"
                    "/test — send a test OTP\n"
                    "/status — check bot status"
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.warning(f"Could not send startup message (owner must /start the bot first): {e}")

        await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())
