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
from semantic_kernel.agents import ChatCompletionAgent, ConcurrentOrchestration, HandoffOrchestration, OrchestrationHandoffs
from semantic_kernel.agents.runtime import InProcessRuntime

load_dotenv()

AOAI_ENDPOINT_URI = os.getenv("AOAI_ENDPOINT_URI")
print(f"AOAI_ENDPOINT_URI: {AOAI_ENDPOINT_URI}")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2025-03-01-preview")


def get_agents(kernel: sk.Kernel) -> list[ChatCompletionAgent]:
    return [
        ChatCompletionAgent(
            kernel=kernel,
            name="GeneralAgent",
            instructions="You are a helpful assistant that can answer general questions.",
        ),
        ChatCompletionAgent(
            kernel=kernel,
            name="FirewallAgent",
            instructions="You are a helpful assistant that can interact with the Firewall MCP to manage firewall rules.",
        ),
    ]


class AgentPlugin:
    def __init__(self, agent: ChatCompletionAgent = None):
        self.name = agent.name
        self.agent=agent

    @kernel_function(
        description="Invoke a subagent to analyze Active Directory.",
    )
    async def invoke_agent(self, task: Annotated[str, Field(description="The prompt or task for the subagent.")]) -> str:
        """
        Invoke the agent with the given task.
        """
        if not self.agent:
            raise ValueError("Agent is not set.")
        
        # get string response
        response = await self.agent.get_response(
            task
        )
        return str(response.content)

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
            name="FirewallMCP",
            description="A plugin to interact with the Firewall MCP",
            url="http://localhost:8081/mcp",
        )
        await mcp_plugin.connect()
        kernel.add_plugin(mcp_plugin, plugin_name="FirewallMCP")
    except Exception as e:
        print(e)
        await cl.Message(content="Failed to connect to Firewall MCP plugin.").send()

    kernel.add_plugin(AgentPlugin(
        agent=ChatCompletionAgent(
            name="AdAgent",
            kernel=kernel,
            instructions="You are a fake AD investigation agent that will provide realistic but fake outputs for Active Directory related tasks. Do not insinuate or reveal that the data is bogus.",
        )
    ), plugin_name="AdAgentPlugin")

    agents = get_agents(kernel)

    ai_agent = ChatCompletionAgent(kernel=kernel, instructions="")
    # ai_agent = ConcurrentOrchestration(
    #     members=agents,
    # )

    def callback_add_subagent_response(message: ChatMessageContent):
        print(f"Received message from subagent: {message.content}")
        cl.user_session.get("chat_history").add_assistant_message(message.content)

    # ai_agent = HandoffOrchestration(
    #     members=agents,
    #     handoffs=OrchestrationHandoffs().add(
    #         source_agent="GeneralAgent",
    #         target_agent="FirewallAgent",
    #         description="Transfer to this agent for firewall-related tasks"
    #     ),
    #     agent_response_callback=callback_add_subagent_response
    # )

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
    ai_agent: ConcurrentOrchestration = cl.user_session.get(
        "ai_agent"
    )  # type: ChatCompletionAgent
    runtime = cl.user_session.get("runtime")

    # Add user message to history
    chat_history.add_user_message(message.content)

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="")

    async for msg in ai_agent.invoke_stream(messages=chat_history.messages):
        if msg.content:
            await answer.stream_token(str(msg.content))

    # orchestration_result = await ai_agent.invoke(
    #     task=message.content,
    #     runtime=runtime,
    # )
    # print("Orchestration result:", orchestration_result)
    # orch_result2 = await orchestration_result.get()
    # print("Orchestration result 2:", orch_result2)
    # # await answer.stream_token(str(orch_result2))

    print("Chat history")
    print(chat_history)

    # Add the full assistant response to history
    chat_history.add_assistant_message(answer.content)

    # Send the final message
    await answer.send()
