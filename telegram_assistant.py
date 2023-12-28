import configparser
import json
import os
import sqlite3
from datetime import timedelta
from typing import List, Union, Dict, Any
from telethon import events
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.photos import DeletePhotosRequest, UploadProfilePhotoRequest
from telethon.tl.types import InputPhoto
from telegrambot import TelegramBot
from openai_assistant import OpenaiAssistant
from openai import OpenAI


class TelegramAssistant(TelegramBot):
    """
    A class to create a Telegram Assistant using the Telethon library.
    """

    def __init__(self, session_file: str, sessions_folder: str, whitelist_users_list: List[str],
                 service_group_username: str,
                 assistant_id: str, thread_id: str):
        """
        Initializes the Telegram Assistant with the provided API id, hash, bot token,
        list of whitelisted users, and service group username.
        """
        # self.client = TelegramClient('assistant', api_id, api_hash).start(bot_token=bot_token)

        # proxy_ip = None
        super().__init__(session_file, sessions_folder=sessions_folder)
        print(f'Created new bot! Phone: {session_file}')

        self.whitelist_users_list = whitelist_users_list
        self.service_group_username = service_group_username

        script_dir = os.path.dirname(__file__)
        session_file_path = os.path.join(script_dir, f'{sessions_folder}/{self.session_file}')

        self.json_file_path = os.path.join(script_dir, f'{sessions_folder}/{self.session_file}.json')
        print(session_file_path)

        config = configparser.ConfigParser()
        config.read('config.ini')
        openai_client = OpenAI(api_key=config['OPENAI']['OPENAI_API_KEY'])

        self.openai_assistant = OpenaiAssistant(openai_client, assistant_id, thread_id)

        print("Connecting...")

    async def start(self):

        # Login
        await self.login_telethon(6, 'eb06d4abfb49dc3eeb1aeb98ae0f581e')

        await self.client.PrintSessions()


    async def get_response(self, message):
        self.openai_assistant.add_message_to_thread(message)
        run = self.openai_assistant.send_command()

        response = self.openai_assistant.get_response(run.id)

        if response['message'] is not None:
            return response['message']
        else:
            action = response['action']
            run_id = response['run_id']
            call_id = response['call_id']

            # Run the action
            function = action['function_name']
            args = json.loads(action['function_args'])

            print(f"Running action {function} with args {args}")

            action_output = await self.call_action(function, args)
            # action_output = asyncio.run(self.call_action(function, args))

            print(f"Action output: {action_output}")

            # Submit the action output
            run = self.openai_assistant.submit_tool_outputs(run_id, str(call_id), action_output)

            # Get the bot response
            response = self.openai_assistant.get_response(run.id)

            if response['message'] is not None:
                return response['message']
            else:
                raise Exception("The bot failed to respond to the action.")

    async def call_action(self, function: str, kwargs: Dict[str, str]):

        print(f"Calling action {function} with args {kwargs}")

        return "test"

    async def event_handler(self, event) -> None:
        """
        Handles incoming events and dispatches commands based on the event content.

        :param event: The event to handle.
        """
        print(event.raw_text)
        # print(event)

        event_sender = await event.get_sender()
        # print(f"Event sender: {event_sender}")
        # print(f"Event chat username: {event.chat.username}")
        # Check if the sender is in the whitelist and if the message is from the service group or a private message
        if (event_sender.username in self.whitelist_users_list) and event.is_private:
            print("Received a command in a DM!")

            response = await self.get_response(event.raw_text)

            # Respond
            await event.respond(response)

        elif event.chat:
            # Command in the service group
            if event.chat.username == self.service_group_username:
                print("Received a command in the service group!")

                # Get the text and handle it with The OpenAI API

                # Get the response from the OpenAI API
                response = await self.get_response(event.raw_text)

                # Respond
                await event.respond(response)

    async def run(self) -> None:
        """
        Starts the Telegram client and listens for events.
        """
        self.client.add_event_handler(self.event_handler, events.NewMessage(incoming=True))
        print("Running Telegram Assistant...")
        await self.client.run_until_disconnected()
