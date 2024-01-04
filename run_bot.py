"""
Run the virtual assistant as the Telegram user bot.
"""

import asyncio

from telegram_assistant import TelegramAssistant
from data import *

if __name__ == '__main__':
    bot = TelegramAssistant(SESSION_FILE, SESSIONS_FOLDER, ['x'], 'x', ASSISTANT_ID,
                            THREAD_ID)

    asyncio.get_event_loop().run_until_complete(bot.start())

    asyncio.get_event_loop().run_until_complete(bot.run())
