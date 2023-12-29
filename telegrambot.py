"""Advanced Telegram class bot to import in different modules
Supporting proxies, official TG API"""
import os
from telethon import TelegramClient as TelegramClientTelethon

import asyncio
import logging

SCRIPT_DIR = os.path.dirname(__file__)

class_logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, session_file: str, sessions_folder: str = "sessions") -> None:
        """
        Class to create user Telegram bots. Can use Opentele for undetected bots (using official API)

        :param session_file: Session file path, can be .session file for Telethon or tdata folder for Opentele
        :param sessions_folder: folder with .session or tdata files
        """
        print(f'Created a new bot! Session: {session_file}')

        # Change it to make the proxies work
        asyncio.set_event_loop(asyncio.SelectorEventLoop())

        self.session_file = session_file

        self.sessions_folder = sessions_folder
        self.client = None
        self.session_file_path = f'{sessions_folder}/{session_file}'

    async def disconnect(self) -> None:
        """
        Disconnect the bot
        :return: None
        """
        try:
            await self.client.disconnect()
            print("Disconnected!")
        except Exception as e1:
            class_logger.error(f'{self.session_file}: ERROR DISCONNECTING! :{e1}')
            print("ERROR DISCONNECTING!")

    async def connect(self) -> None:
        print("Connecting...")
        await asyncio.wait_for(self.client.connect(), 20)

        class_logger.debug(f'{self.session_file}: Connected!')

    async def login_telethon(self, api_id: int, api_hash: str) -> None:
        """
        Login to the bot using Telethon
        :param api_id: Telegram API ID
        :param api_hash: Telegram API hash
        """
        # self.client = TelegramClient(session_file_path, api_id, api_hash)
        self.client = TelegramClientTelethon(self.session_file_path, api_id=api_id, api_hash=api_hash, timeout=20)

        await self.connect()

