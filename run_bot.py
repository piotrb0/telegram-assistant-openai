"""
Run the virtual assistant as the Telegram user bot.
"""

import asyncio

from telegram_assistant import TelegramAssistant
from data import *

if __name__ == '__main__':
    group = os.getenv('GROUP')
    bot = TelegramAssistant(SESSION_FILE, SESSIONS_FOLDER, API_ID, API_HASH, [group], group, ASSISTANT_ID,
                            THREAD_ID)

    asyncio.get_event_loop().run_until_complete(bot.start(IP, PORT, USERNAME, PASSWORD))

    asyncio.get_event_loop().run_until_complete(bot.run())
