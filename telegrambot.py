"""Advanced Telegram class bot to import in different modules
Supporting proxies, official TG API"""
import configparser
import csv
import json
import os
import random
import re
import string
import time

import socks
from telethon import events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.messages import StartBotRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon import errors
from telethon import TelegramClient as TelegramClientTelethon

import asyncio
import logging

import concurrent
from concurrent.futures import ThreadPoolExecutor

from opentele.td import TDesktop
from opentele.tl import TelegramClient
from opentele.api import API, UseCurrentSession

SCRIPT_DIR = os.path.dirname(__file__)

class_logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, session_file: str, sessions_folder: str = "sessions") -> None:
        print(f'Created a new bot! Session: {session_file}')

        # Change it to make the proxies work
        asyncio.set_event_loop(asyncio.SelectorEventLoop())

        self.session_file = session_file

        self.sessions_folder = sessions_folder
        self.client = None
        self.session_file_path = f'{sessions_folder}/{session_file}'

    async def disconnect(self) -> None:
        try:
            await self.client.disconnect()
            print("Disconnected!")
        except Exception as e1:
            class_logger.error(f'{self.session_file}: ERROR DISCONNECTING! :{e1}')
            print("ERROR DISCONNECTING!")

    async def login_telethon(self, api_id: int, api_hash: str) -> None:
        # self.client = TelegramClient(session_file_path, api_id, api_hash)
        self.client = TelegramClientTelethon(self.session_file_path, api_id=api_id, api_hash=api_hash, timeout=20)

        await self.client.connect()

