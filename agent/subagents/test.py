import asyncio
from dotenv import load_dotenv
import os

from semantic_kernel.agents import AzureResponsesAgent
from semantic_kernel.connectors.ai.open_ai import AzureOpenAISettings
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents import AuthorRole, TextContent

load_dotenv()

AOAI_ENDPOINT_URI = os.getenv("AOAI_ENDPOINT_URI")
print(f"AOAI_ENDPOINT_URI: {AOAI_ENDPOINT_URI}")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2025-01-01-preview")

async def main():
    # Set up the client and model using Azure OpenAI Resources
    client = AzureResponsesAgent.create_client(
        # base_url=AOAI_ENDPOINT_URI,
        endpoint=AOAI_ENDPOINT_URI,
        api_key=AOAI_API_KEY,
        deployment_name="o4-mini",
        api_version=AOAI_API_VERSION,
    )

    # Create the AzureResponsesAgent instance using the client and the model
    agent = AzureResponsesAgent(
        ai_model_id="o4-mini",
        client=client,
        instructions="your instructions",
        name="name",
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
    asyncio.run(main())    