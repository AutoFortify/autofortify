import chainlit as cl
import semantic_kernel as sk
import os
from typing import Annotated
from pydantic import Field
from dotenv import load_dotenv
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.functions import kernel_function
from semantic_kernel.contents import ChatHistory, ChatMessageContent
from semantic_kernel.connectors.mcp import MCPSsePlugin
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.agents.runtime import InProcessRuntime

load_dotenv()

AOAI_ENDPOINT_URI = os.getenv("AOAI_ENDPOINT_URI")
print(f"AOAI_ENDPOINT_URI: {AOAI_ENDPOINT_URI}")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2025-03-01-preview")


@cl.on_chat_start
async def on_chat_start():
    kernel = sk.Kernel()

    ai_service = AzureChatCompletion(
        endpoint=AOAI_ENDPOINT_URI,
        api_key=AOAI_API_KEY,
        deployment_name="o4-mini",
        api_version=AOAI_API_VERSION,
    )

    kernel.add_service(ai_service)

    try:
        mcp_plugin = MCPSsePlugin(
            name="ActiveDirectoryAndServicesMCP",
            description="MCP functionality for Active Directory and Services modifications",
            url="http://localhost:8081/mcp",
        )
        await mcp_plugin.connect()
        kernel.add_plugin(mcp_plugin, plugin_name="ActiveDirectoryAndServicesMCP")
    except Exception as e:
        print(e)
        await cl.Message(content="Failed to connect to ActiveDirectoryAndServices MCP plugin.").send()

    ai_agent = ChatCompletionAgent(kernel=kernel, instructions="""
You are an expert in security hardening and system administration regarding Active Directory and Windows systems.
                                   
Users will ask you to perform tasks related to user account management, firewall rules, and system hardening.

You have access to tools to retrieve active directory information, modify user accounts, and manage firewall rules.
Before running any commands that will modify the system, you will ask for confirmation from the user.
You will always provide a summary of the actions you are about to take before executing them.
Be transparent with reasoning and offer suggestions for hardening the system based on best practices.
""")

    runtime = InProcessRuntime()
    runtime.start()

    _ = cl.SemanticKernelFilter(kernel=kernel)

    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_history", ChatHistory())
    cl.user_session.set("ai_agent", ai_agent)
    cl.user_session.set("runtime", runtime)


@cl.on_message
async def on_message(message: cl.Message):
    kernel = cl.user_session.get("kernel")  # type: sk.Kernel
    ai_service = cl.user_session.get("ai_service")  # type: AzureChatCompletion
    chat_history = cl.user_session.get("chat_history")  # type: ChatHistory
    ai_agent = cl.user_session.get("ai_agent")  # type: ChatCompletionAgent
    runtime = cl.user_session.get("runtime")

    # Add user message to history
    chat_history.add_user_message(message.content)

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="")

    async for msg in ai_agent.invoke_stream(messages=chat_history.messages):
        if msg.content:
            await answer.stream_token(str(msg.content))

    print("Chat history")
    print(chat_history)

    # Add the full assistant response to history
    chat_history.add_assistant_message(answer.content)

    # Send the final message
    await answer.send()
