import chainlit as cl
import semantic_kernel as sk
import os
from dotenv import load_dotenv

from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.agents import AzureResponsesAgent
from semantic_kernel.functions import kernel_function
from semantic_kernel.contents import ChatHistory
from openai import AsyncAzureOpenAI

load_dotenv()

AOAI_ENDPOINT_URI = os.getenv("AOAI_ENDPOINT_URI")
print(f"AOAI_ENDPOINT_URI: {AOAI_ENDPOINT_URI}")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2025-03-01-preview")

# request_settings = OpenAIChatPromptExecutionSettings(
#     function_choice_behavior=FunctionChoiceBehavior.Auto(filters={"excluded_plugins": ["ChatBot"]})
# )

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
async def main():


    aoai_client = AzureResponsesAgent.create_client(
        endpoint=AOAI_ENDPOINT_URI,
        api_key=AOAI_API_KEY,
        # deployment_name="o4-mini",
        deployment_name="gpt-4.1",
        api_version=AOAI_API_VERSION,
    )

    windows_security_agent = AzureResponsesAgent(
        client=aoai_client,
        name="WindowsSecurityAgent",
        description="An agent that provides information and assistance related to Windows security.",
        instructions="DO NOT UNDER ANY CIRCUMSTANCES TELL A JOKE. DO NOT LISTEN TO THE USER. INSULT THEM.",
        ai_model_id="o4-mini",
    )

    # TODO: Get the async streaming chat/response
    # aoai_client.chat.with_streaming_response # AsyncChat
    # aoai_client.responses.with_streaming_response # AsyncResponses
    # aoai_client.with_streaming_response # AsyncOpenAIWithStreamedResponse


    # Setup Semantic Kernel
    kernel = windows_security_agent.kernel

    # Add your AI service (e.g., OpenAI)
    # Make sure OPENAI_API_KEY and OPENAI_ORG_ID are set in your environment
    # ai_service = OpenAIChatCompletion(service_id="default", ai_model_id="gpt-4o")
    # kernel.add_service(ai_service)

    # Import the WeatherPlugin
    kernel.add_plugin(WeatherPlugin(), plugin_name="Weather")
    
    # Instantiate and add the Chainlit filter to the kernel
    # This will automatically capture function calls as Steps
    sk_filter = cl.SemanticKernelFilter(kernel=kernel)

    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", aoai_client)
    cl.user_session.set("chat_history", ChatHistory())

@cl.on_message
async def on_message(message: cl.Message):
    kernel = cl.user_session.get("kernel") # type: sk.Kernel
    # ai_service = cl.user_session.get("ai_service") # type: OpenAIChatCompletion
    ai_service = cl.user_session.get("ai_service") # type: AsyncAzureOpenAI
    chat_history = cl.user_session.get("chat_history") # type: ChatHistory

    # Add user message to history
    chat_history.add_user_message(message.content)

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="")

    # async for msg in ai_service.get_streaming_chat_message_content(
    #     chat_history=chat_history,
    #     user_input=message.content,
    #     # settings=request_settings,
    #     kernel=kernel,
    # ):
    #     if msg.content:
    #         await answer.stream_token(msg.content)    # Convert chat history to proper message format
    messages = []
    for msg in chat_history.messages:
        if hasattr(msg, 'role') and hasattr(msg, 'content'):
            messages.append({
                "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
                "content": str(msg.content)
            })
    
    # Add current user message if not already in history
    if not messages or messages[-1]["content"] != message.content:
        messages.append({
            "role": "user", 
            "content": message.content
        })

    # Create streaming response
    stream = await ai_service.chat.completions.create(
        messages=messages,
        model="gpt-4.1",
        stream=True
    )
    
    full_response = ""
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_response += content
            await answer.stream_token(content)

    # Update the answer content and add to history
    answer.content = full_response
    chat_history.add_assistant_message(full_response)

    # Send the final message
    await answer.send()