import asyncio
from fastmcp import Client
from fastmcp.client.transports import (
    StreamableHttpTransport,
    StdioTransport,
    SSETransport,
)
import yaml

MCP_SERVER_URL = "http://127.0.0.1:8081/mcp"


async def list_tools_from_mcp_server(server_url: str):
    transport = StreamableHttpTransport(url=server_url)
    tool_info = []
    async with Client(SSETransport("http://127.0.0.1:8081/mcp")) as client:
        tools = await client.list_tools()
        if not tools:
            print("No tools found on the server.")
            return
        for tool in tools:
            tool_data = {}
            tool_data["Name"] = tool.name.strip()
            tool_data["Description"] = tool.description.strip()
            tool_data["Inputs"] = []
            for param, param_info in tool.inputSchema.get("properties", {}).items():
                param_data = {
                    "Name": param.strip(),
                    "Description": param_info.get(
                        "description", "No description"
                    ).strip(),
                }
                tool_data["Inputs"].append(param_data)
            tool_info.append(tool_data)
    print(yaml.dump(tool_info, sort_keys=False, allow_unicode=True))


if __name__ == "__main__":
    asyncio.run(list_tools_from_mcp_server(MCP_SERVER_URL))
