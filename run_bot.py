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

    # Load proxy info from env variables
    proxy_ip = os.getenv('PROXY_IP')
    proxy_port = int(os.getenv('PROXY_PORT'))
    proxy_username = os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('PROXY_PASSWORD')

    asyncio.get_event_loop().run_until_complete(bot.start(proxy_ip, proxy_port, proxy_username, proxy_password))

    asyncio.get_event_loop().run_until_complete(bot.run())
