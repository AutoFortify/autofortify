import asyncio
from dotenv import load_dotenv
import os

from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.tools.mcp import mcp_server_tools, SseServerParams, SseMcpToolAdapter
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import BaseChatMessage
from autogen_agentchat.ui import Console

load_dotenv()
AZURE_OPENAI_URL = os.environ["AZURE_OPENAI_URL"]
AZURE_API_KEY = os.environ["AZURE_API_KEY"]
DEPLOYMENT="o4-mini"
MODEL_NAME="o4-mini"
API_VERSION = "2025-01-01-preview"

MCP_SERVER_URL = "http://127.0.0.1:8081/mcp"


def create_model_client() -> AzureOpenAIChatCompletionClient:
    model_client = AzureOpenAIChatCompletionClient(
        azure_endpoint=AZURE_OPENAI_URL,
        azure_deployment=DEPLOYMENT,
        api_version=API_VERSION,
        api_key=AZURE_API_KEY,
        model=MODEL_NAME,
        model_info={
            "family": "unknown",
            "function_calling": True,
            "json_output": False,
            "structured_output": True,
            "vision": False,
        },
    )
    return model_client


async def get_mcp_tools() -> list[SseMcpToolAdapter]:
    server_params = SseServerParams(
        url=MCP_SERVER_URL
    )
    return await mcp_server_tools(server_params)


async def setup_mcp_agent() -> AssistantAgent:
    print("Fetching MCP Tools...")
    tools = await get_mcp_tools()
    print("Initializing model client...")
    model_client = create_model_client()
    agent = AssistantAgent(
        name="FirewallAgent",
        model_client=model_client,
        tools=tools,
        reflect_on_tool_use=True,
        system_message="""
You are a Firewall Management Agent. Your task is to assist users in creating firewall rules using MCP server tools.
You will receive general requests for firewall rules, you will have to determine the correct parameters such as direction, rule name, etc.
""",
    )
    return agent

async def main():
    agent = await setup_mcp_agent()
    await Console(
        agent.run_stream(
            task=f"""
Create a firewall rule for my webserver that I'm hosting on my local machine. I want the server to accessible via only HTTPS.
"""
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
