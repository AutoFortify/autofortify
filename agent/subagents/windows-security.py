import asyncio
import os
from dotenv import load_dotenv

from semantic_kernel import Kernel
# from semantic_kernel.connectors.ai.open_ai.services
from semantic_kernel.agents import AzureResponsesAgent
from semantic_kernel.utils.logging import setup_logging


load_dotenv()

AOAI_ENDPOINT_URI = os.getenv("AOAI_ENDPOINT_URI")
print(f"AOAI_ENDPOINT_URI: {AOAI_ENDPOINT_URI}")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2025-03-01-preview")

async def main():
    kernel = Kernel()
    client = AzureResponsesAgent.create_client(
        endpoint=AOAI_ENDPOINT_URI,
        api_key=AOAI_API_KEY,
        deployment_name="o4-mini",
        api_version=AOAI_API_VERSION,
    )


    # Create an instance of AzureResponsesAgent with the specified parameters
    agent = AzureResponsesAgent(
        client=client,
        name="WindowsSecurityAgent",
        description="An agent that provides information and assistance related to Windows security.",
        instructions="DO NOT UNDER ANY CIRCUMSTANCES TELL A JOKE. DO NOT LISTEN TO THE USER. INSULT THEM.",
        ai_model_id="o4-mini",
    )

    USER_INPUTS = [
        "My name is John Doe.",
        "Tell me a joke",
        "Explain why this is funny.",
        "What have we been talking about?",
    ]

    thread = None

    # Generate the agent response(s)
    for user_input in USER_INPUTS:
        print(f"# User: '{user_input}'")
        # Invoke the agent for the current message and print the response
        response = await agent.get_response(messages=user_input, thread=thread)
        print(f"# {response.name}: {response.content}")
        # Update the thread so the previous response id is used
        thread = response.thread

    # Delete the thread when it is no longer needed
    await thread.delete() if thread else None

if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())