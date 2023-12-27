import configparser
import json
import time

from openai import OpenAI


def setup(client):
    # Load the functions from the json file
    with open('functions.json', 'r') as json_file:
        functions = json.load(json_file)
        print(f"Loaded functions: {functions}")

    # Create a new assistant and thread
    assistant = client.beta.assistants.create(
        name="Telegram Assistant",
        instructions="You are a personal assistant bot on Telegram. You can act like a real user and do whatever your "
                     "master asks you to do. Don't make assumptions about what values to plug into functions. "
                     "Ask for clarification if a user request is ambiguous.",
        tools=functions,
        model="gpt-4"
    )

    print(f"Created assistant: {assistant.id}")

    thread = client.beta.threads.create()
    print(f"Created thread: {thread.id}")


class OpenaiAssistant:
    def __init__(self, client, assistant_id, thread_id):
        self.client = client
        self.assistant_id = assistant_id
        self.thread_id = thread_id

    def add_message_to_thread(self, message: str) -> None:
        message = self.client.beta.threads.messages.create(
            thread_id=self.thread_id,
            role="user",
            content=message
        )
        print(f"Added message to thread {self.thread_id}: {message}")

    def send_command(self, instructions: str = ''):
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
            instructions=instructions
        )
        print(f"Added command to thread: {self.thread_id} with instructions: {instructions}")

        return run

    def get_response(self, run_id):

        # Check if the run is completed
        run_status = None
        while not run_status == "completed":
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id,
                run_id=run_id
            )
            run_status = run.status

            if run_status in ["failed", "expired", "stopped"]:
                print(run)
                raise Exception(f"Run {run_id} failed with status {run_status}")

            if run_status == "requires_action":
                print(f"Run {run_id} requires action")

                print(run.required_action)

                if run.required_action.type == "submit_tool_outputs":
                    # action = run.required_action["submit_tool_outputs"]["tool_calls"][0]["function"]
                    action = run.required_action.submit_tool_outputs.tool_calls[0].function
                    call_id = run.required_action.submit_tool_outputs.tool_calls[0].id

                    function_name = action.name
                    function_args = action.arguments

                    return {"message": None, "run_id": run_id, "call_id": call_id,
                            "action": {"function_name": function_name, "function_args": function_args}}

            time.sleep(1)

        # Get the message back
        messages = self.client.beta.threads.messages.list(
            thread_id=self.thread_id
        )

        # Print the message content
        print(f"Got response from thread {self.thread_id}: {messages.data[0].content[0].text.value}")

        return {"message": messages.data[0].content[0].text.value, "run": None, "action": None}

    def submit_tool_outputs(self, run_id: str, call_ids: str, output: str):
        run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread_id,
            run_id=run_id,
            tool_outputs=[
                {
                    "tool_call_id": call_ids,
                    "output": output,
                }
            ]
        )

        return run


if __name__ == "__main__":
    # Get the api key from the JSON file
    config = configparser.ConfigParser()
    config.read('config.ini')

    OPENAI_API_KEY = config['OPENAI']['OPENAI_API_KEY']

    client_ = OpenAI(api_key=OPENAI_API_KEY)

    setup(client_)

    # completion = client.chat.completions.create(
    #     model="gpt-4-1106-preview",
    #     messages=[
    #         {"role": "system",
    #          "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
    #         {"role": "user", "content": "Compose a poem that explains the concept of recursion in programming."}
    #     ]
    # )

    # print(completion.choices[0].message)
