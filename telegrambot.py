"""Advanced Telegram class bot to import in different modules
Supporting proxies, official TG API"""
import os
from telethon import TelegramClient as TelegramClientTelethon

import asyncio
import logging
import socks

SCRIPT_DIR = os.path.dirname(__file__)

class_logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, session_file: str, api_id: int, api_hash: str, sessions_folder: str = "sessions") -> None:
        """
        Class to create user Telegram bots. Can use Opentele for undetected bots (using official API)

        :param session_file: Session file path, can be .session file for Telethon or tdata folder for Opentele
        :param sessions_folder: folder with .session or tdata files
        """
        print(f'Created a new bot! Session: {session_file}')

        # Change it to make the proxies work
        asyncio.set_event_loop(asyncio.SelectorEventLoop())

        self.session_file = session_file
        self.api_id = api_id
        self.api_hash = api_hash

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

    async def login_telethon(self, proxy_ip: str = None, proxy_port: int = None, proxy_username: str = None,
                             proxy_password: str = None) -> None:
        """
        Login to the bot using Telethon
        :param proxy_ip: Proxy IP (optional)
        :param proxy_port: Proxy port (optional)
        :param proxy_username: Proxy username (optional)
        :param proxy_password: Proxy password (optional)
        """
        # self.client = TelegramClient(session_file_path, api_id, api_hash)
        print(self.session_file_path)

        if all([proxy_ip, proxy_port, proxy_username, proxy_password]):
            print(f'Connecting with proxy: {proxy_ip}:{proxy_port}')
            proxy = (socks.HTTP, proxy_ip, proxy_port, True, proxy_username, proxy_password)
            self.client = TelegramClientTelethon(self.session_file_path, api_id=self.api_id, api_hash=self.api_hash,
                                                 timeout=20, proxy=proxy)
        else:
            self.client = TelegramClientTelethon(self.session_file_path, api_id=self.api_id, api_hash=self.api_hash,
                                                 timeout=20)
        await self.connect()
