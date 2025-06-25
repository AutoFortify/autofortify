import chainlit as cl
import semantic_kernel as sk
import os
from dotenv import load_dotenv
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.functions import kernel_function
from semantic_kernel.contents import ChatHistory

load_dotenv()

AOAI_ENDPOINT_URI = os.getenv("AOAI_ENDPOINT_URI")
print(f"AOAI_ENDPOINT_URI: {AOAI_ENDPOINT_URI}")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2025-03-01-preview")

request_settings = AzureChatPromptExecutionSettings(
    function_choice_behavior=FunctionChoiceBehavior.Auto(filters={"excluded_plugins": ["ChatBot"]})
)

# Example Native Plugin (Tool)
class WeatherPlugin:
    @kernel_function(name="get_weather", description="Gets the weather for a city")
    def get_weather(self, city: str) -> str:
        """Retrieves the weather for a given city."""
        if "paris" in city.lower():
            return f"The weather in {city} is 20°C and sunny."
        elif "london" in city.lower():
            return f"The weather in {city} is 15°C and cloudy."
        else:
            return f"Sorry, I don't have the weather for {city}."

@cl.on_chat_start
async def on_chat_start():
    # Setup Semantic Kernel
    kernel = sk.Kernel()

    # Add your AI service (e.g., OpenAI)
    # Make sure OPENAI_API_KEY and OPENAI_ORG_ID are set in your environment
    ai_service = AzureChatCompletion(
        endpoint=AOAI_ENDPOINT_URI,
        api_key=AOAI_API_KEY,
        # deployment_name="o4-mini",
        deployment_name="gpt-4.1",
        api_version=AOAI_API_VERSION,
    )
    kernel.add_service(ai_service)

    # Import the WeatherPlugin
    kernel.add_plugin(WeatherPlugin(), plugin_name="Weather")
    
    # Instantiate and add the Chainlit filter to the kernel
    # This will automatically capture function calls as Steps
    sk_filter = cl.SemanticKernelFilter(kernel=kernel)

    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_history", ChatHistory())

@cl.on_message
async def on_message(message: cl.Message):
    kernel = cl.user_session.get("kernel") # type: sk.Kernel
    ai_service = cl.user_session.get("ai_service") # type: AzureChatCompletion
    chat_history = cl.user_session.get("chat_history") # type: ChatHistory

    # Add user message to history
    chat_history.add_user_message(message.content)

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="")

    async for msg in ai_service.get_streaming_chat_message_content(
        chat_history=chat_history,
        user_input=message.content,
        settings=request_settings,
        kernel=kernel,
    ):
        if msg.content:
            await answer.stream_token(msg.content)

    # Add the full assistant response to history
    chat_history.add_assistant_message(answer.content)

    # Send the final message
    await answer.send()