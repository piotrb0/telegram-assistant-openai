"""
Cancel a run in a OpenAI thread. Use it when you get an error while using the bot and want to run the assistant
again with another run.
"""
from openai import OpenAI
from data import OPENAI_API_KEY

if __name__ == "__main__":
    THREAD = ""

    client = OpenAI(api_key=OPENAI_API_KEY)
    runs = client.beta.threads.runs.list(THREAD)

    for run in runs:
        # Cancel the run if it's still running
        if run.status in ["running", "requires_action"]:
            print(f"Canceling run {run.id}")
            client.beta.threads.runs.cancel(
                thread_id=THREAD,
                run_id=run.id
            )