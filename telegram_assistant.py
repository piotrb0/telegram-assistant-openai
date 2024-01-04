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

    def __init__(self, session_file: str, sessions_folder: str, api_id: int, api_hash: str,
                 whitelist_users_list: List[str], service_group_username: str, assistant_id: str, thread_id: str):
        """
        Initializes the Telegram Assistant with the provided API id, hash, bot token,
        list of whitelisted users, and service group username.
        """
        # self.client = TelegramClient('assistant', api_id, api_hash).start(bot_token=bot_token)

        # proxy_ip = None
        super().__init__(session_file, api_id, api_hash, sessions_folder=sessions_folder)
        print(f'Created new bot! Phone: {session_file}')

        self.whitelist_users_list = whitelist_users_list
        self.service_group_username = service_group_username

        # Load the groups to watch from the db
        self.groups_to_watch = self.get_groups_to_watch()['info']
        print(f"Groups to watch: {self.groups_to_watch}")

        self.initialize_database()

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
        await self.login_telethon()

        # Check if the bot is in the service group and if not, join it
        if not await self.is_bot_in_group(self.service_group_username):
            await self.join_channel(self.service_group_username)

    def initialize_database(self) -> None:
        """
        Initializes the SQLite database with tables for storing information about
        groups/channels and messages.
        """
        with sqlite3.connect('assistant.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS joined_groups
                           (id INTEGER PRIMARY KEY, entity TEXT, access_hash TEXT, timestamp_joined INTEGER)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS messages
                           (id INTEGER PRIMARY KEY, from_id INTEGER, group_username TEXT, 
                           message TEXT, timestamp_sent INTEGER)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS groups_to_watch
                           (id INTEGER PRIMARY KEY, group_username TEXT)''')
            conn.commit()

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

            print(f"Action output: {action_output}")

            # Submit the action output
            run = self.openai_assistant.submit_tool_outputs(run_id, str(call_id), action_output)

            # Get the bot response
            response = self.openai_assistant.get_response(run.id)

            if response['message'] is not None:
                return response['message']
            else:
                raise Exception("The bot failed to respond to the action.")

    async def call_action(self, function: str, kwargs: Dict[str, str]) -> str:
        """
        Calls an action with the provided arguments.

        :param function: The name of the function to call.
        :param kwargs: A dictionary containing the arguments to pass to the function.
        :return: The output of the function.
        """
        if function == "get_data_from_db":
            return str(self.get_data_from_db(**kwargs))
        elif function == "is_bot_in_group":
            return str(await self.is_bot_in_group(**kwargs))
        elif function == "join_channel":
            return str(await self.join_channel(**kwargs))
        elif function == "leave_channel":
            return str(await self.leave_channel(**kwargs))
        elif function == "send_message":
            return str(await self.send_message(**kwargs))
        elif function == "get_conversation_history":
            return str(await self.get_conversation_history(**kwargs))
        elif function == "get_groups_to_watch":
            return str(self.get_groups_to_watch())
        elif function == "add_group_to_watchlist":
            return str(self.add_group_to_watchlist(**kwargs))

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

            # Message in a group or channel
            elif event.chat.username in self.groups_to_watch:
                print("Received a message in a group or channel!")

                # group_id = event.message.peer_id.channel_id
                group_username = event.chat.username
                from_id = event.message.from_id
                with sqlite3.connect('assistant.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'INSERT INTO messages (from_id, group_username, message, timestamp_sent) VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
                        (from_id, group_username, event.raw_text))
                    conn.commit()

    async def is_bot_in_group(self, entity: str) -> dict[str, Union[str, bool, None]]:
        """
        Checks if the bot is in a group or channel.

        :param entity: The username or ID of the group or channel.
        :return: A dictionary containing the result of the check, info == True if the bot is in the group or channel,
        info == False if the bot is not in the group or channel, and error == None if the check was successful,
        otherwise error contains the error message.
        """
        try:
            async for dialog in self.client.iter_dialogs():
                print(dialog.entity.username)
                if dialog.entity.username == entity:
                    return {'success': True, 'info': True, 'error': None}

            return {'success': True, 'info': False, 'error': None}
        except Exception as e:
            print(e)
            return {'success': False, 'info': None, 'error': str(e)}

    async def change_profilepic(self, pic):
        """
        Changes the profile picture to the provided image.
        :param pic: New profile picture
        :return: A dictionary containing the result of the query, info == True photo has been changed successfully,
        otherwise info == False, and error == None if the query was successful, otherwise error contains
        the error message.
        """
        try:
            await self.client(UploadProfilePhotoRequest(
                file=await self.client.upload_file(pic)
            ))
            return {'success': True, 'info': None, 'error': None}
        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    async def delete_old_profile_photo(self):
        """
        Deletes the old profile photo.
        :return: A dictionary containing the result of the query, info == True if the profile photo was deleted
        successfully, otherwise info == False, and error == None if the query was successful, otherwise error contains
        the error message.
        """
        try:
            print("Deleting the old profile photo...")
            p = await self.client.get_profile_photos('me')
            p = p[-1]
            await self.client(DeletePhotosRequest(
                id=[InputPhoto(
                    id=p.id,
                    access_hash=p.access_hash,
                    file_reference=p.file_reference
                )]
            ))
            return {'success': True, 'info': None, 'error': None}
        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    async def join_channel(self, entity: str) -> dict[str, Union[str, bool, None]]:
        """
        Joins a channel or group and adds it to the database.

        :param entity: The username or ID of the channel or group to join.
        :return: A dictionary containing the result of the query, info == True if the channel or group was joined
        successfully, otherwise info == False, and error == None if the query was successful, otherwise error contains
        the error message.
        """
        try:
            print("Joining the channel...")
            await self.client(JoinChannelRequest(entity))
            entity_obj = await self.client.get_entity(entity)
            with sqlite3.connect('assistant.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO joined_groups (entity, access_hash, timestamp_joined) VALUES (?, ?, CURRENT_TIMESTAMP)',
                    (entity_obj.username, str(entity_obj.access_hash)))
                conn.commit()

            return {'success': True, 'info': None, 'error': None}
        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    async def leave_channel(self, entity: str) -> dict[str, Union[str, bool, None]]:
        """
        Leaves a channel or group and removes it from the database.

        :param entity: The username or ID of the channel or group to leave.
        :return: A dictionary containing the result of the query, info == True if the channel or group was left
        successfully, otherwise info == False, and error == None if the query was successful, otherwise error contains
        the error message.
        """
        try:
            await self.client(LeaveChannelRequest(entity))
            with sqlite3.connect('assistant.db') as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM joined_groups WHERE entity = ?', (entity,))
                conn.commit()

            return {'success': True, 'info': None, 'error': None}
        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    async def send_message(self, entity: str, message: str, schedule: timedelta = None) -> dict[str, Union[str, bool, None]]:
        """
        Sends a message to a specified group or channel.

        :param entity: The username or ID of the channel or group to send the message to.
        :param message: The message to send.
        :param schedule: The time to wait before sending the message.
        :return: A dictionary containing the result of the query, info == True if the message was sent successfully,
        otherwise info == False, and error == None if the query was successful, otherwise error contains the error
        message.
        """
        try:
            await self.client.send_message(entity, message, schedule=schedule)
            return {'success': True, 'info': None, 'error': None}
        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    async def add_comment(self, entity: str, message: str,
                          comment_to_message_id: int, schedule: timedelta = None) -> dict[str, Union[str, bool, None]]:
        """
        Adds a comment to a specified group or channel.

        :param entity: The username or ID of the channel or group to send the message to.
        :param message: The message to send.
        :param comment_to_message_id: The message to reply to.
        :param schedule: The time to wait before sending the message.
        :return: A dictionary containing the result of the query, info == True if the message was sent successfully,
        otherwise info == False, and error == None if the query was successful, otherwise error contains the error
        message.
        """
        try:
            comment = await self.client.send_message(entity=entity, message=message, comment_to=comment_to_message_id,
                                                     schedule=schedule)

            print(comment)
            return {'success': True, 'info': None, 'error': None}
        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    async def get_conversation_history(self, entity: str, limit: int = 20) -> dict[str, Union[None, bool, list[Any]]]:
        """
        Gets the conversation history for a specified group, channel or user.

        :param entity: The username or ID of the channel, group or user to get the conversation history for.
        :param limit: The number of messages to retrieve. Defaults to 20.
        :return: A dictionary containing the result of the query, info contains the list of the messages if successful,
        otherwise info is None, success == True if the query was successful, otherwise success == False, and error
        contains the error message if the query failed, otherwise error is None.
        """
        try:
            messages = []
            async for message in self.client.iter_messages(entity, limit=limit):
                # print(message)
                sender = await message.get_sender()
                messages.append(
                    {'id': message.id, 'sender': sender.username, 'text': message.text, 'date': message.date})
            return {'success': True, 'info': messages, 'error': None}
        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    async def run(self) -> None:
        """
        Starts the Telegram client and listens for events.
        """
        self.client.add_event_handler(self.event_handler, events.NewMessage(incoming=True))
        print("Running Telegram Assistant...")
        await self.client.run_until_disconnected()

    def get_data_from_db(self, query: str) -> dict[str, Union[None, bool, list[Any]]]:
        """
        Use this function to get the data from the database. Input should be a fully formed SQL query.

        :param query: The query to execute.
        :return: A dictionary containing the result of the query, info contains the result of the query if successful,
        otherwise info is None, success == True if the query was successful, otherwise success == False, and error
        contains the error message if the query failed, otherwise error is None.
        """
        try:
            with sqlite3.connect('assistant.db') as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return {'success': True, 'info': cursor.fetchall(), 'error': None}

        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    def get_groups_to_watch(self) -> dict[str, Union[None, bool, list[str]]]:
        """
        Gets the groups to watch from the database.

        :return: A dictionary containing the result of the query, info contains the result of the query if successful,
        otherwise info is None, success == True if the query was successful, otherwise success == False, and error
        contains the error message if the query failed, otherwise error is None.
        """
        try:
            with sqlite3.connect('assistant.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT group_username FROM groups_to_watch')

                groups_to_watch = []
                for group in cursor.fetchall():
                    groups_to_watch.append(group[0].replace('@', '').replace('https://t.me/', ''))

                return {'success': True, 'info': groups_to_watch, 'error': None}

        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    def add_group_to_watchlist(self, group_username: str) -> dict[str, Union[None, bool, str]]:
        """
        Adds a group to the watchlist.

        :param group_username: The group to add to the watchlist.
        :return: A dictionary containing the result of the query, info contains the result of the query if successful,
        otherwise info is None, success == True if the query was successful, otherwise success == False, and error
        contains the error message if the query failed, otherwise error is None.
        """
        try:
            with sqlite3.connect('assistant.db') as conn:
                cursor = conn.cursor()

                group_username = group_username.replace('@', '').replace('https://t.me/', '')
                cursor.execute('INSERT INTO groups_to_watch (group_username) VALUES (?)', (group_username,))
                conn.commit()

                self.groups_to_watch = self.get_groups_to_watch()['info']
                return {'success': True, 'info': None, 'error': None}

        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}

    def remove_group_from_watchlist(self, group_username: str) -> dict[str, Union[None, bool, str]]:
        """
        Removes a group from the watchlist.

        :param group_username: The group to remove from the watchlist.
        :return: A dictionary containing the result of the query, info contains the result of the query if successful,
        otherwise info is None, success == True if the query was successful, otherwise success == False, and error
        contains the error message if the query failed, otherwise error is None.
        """
        try:
            with sqlite3.connect('assistant.db') as conn:
                cursor = conn.cursor()

                group_username = group_username.replace('@', '').replace('https://t.me/', '')
                cursor.execute('DELETE FROM groups_to_watch WHERE group_username = ?', (group_username,))
                conn.commit()

                self.groups_to_watch = self.get_groups_to_watch()['info']
                return {'success': True, 'info': None, 'error': None}

        except Exception as e:
            return {'success': False, 'info': None, 'error': str(e)}
