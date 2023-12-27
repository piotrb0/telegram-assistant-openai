import configparser
import json

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
