from fastmcp.server import FastMCP
from typing import Annotated, Literal
from pydantic import Field
import os

SIMULATE_MODIFICATIONS = True

mcp = FastMCP()


@mcp.tool(
    name="create_firewall_rule",
    description="Creates and enables a firewall rule with the specified parameters.",
    annotations={"title": "Create Firewall Rule"},
)
def create_firewall_rule(
    rule_name: Annotated[str, Field(description="Name of the firewall rule")],
    display_name: Annotated[str, Field(description="Display name for the rule")],
    action: Annotated[
        Literal["Allow", "Deny"],
        Field(description="Action for the rule ('Allow' or 'Deny')"),
    ],
    local_port: Annotated[int, Field(description="Local port number")],
    protocol: Annotated[
        Literal["TCP", "UDP"],
        Field(description="Protocol for the rule ('TCP' or 'UDP')"),
    ],
    direction: Annotated[
        Literal["Inbound", "Outbound"],
        Field(description="Direction of the rule ('Inbound' or 'Outbound')"),
    ],
) -> str:
    print(
        f"Creating firewall rule with parameters:\n"
        f"Name: {rule_name}\n"
        f"Display Name: {display_name}\n"
        f"Action: {action}\n"
        f"Local Port: {local_port}\n"
        f"Protocol: {protocol}\n"
        f"Direction: {direction}"
    )
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        res = os.system(
            "powershell.exe -Command "
            f"New-NetFirewallRule -Name '{rule_name}' -DisplayName '{display_name}' "
            f"-Action {action} -LocalPort {local_port} -Protocol {protocol} -Direction {direction} -Enabled True"
        )
    if res == 0:
        return f"Firewall rule '{rule_name}' created successfully."
    else:
        return f"Failed to create firewall rule '{rule_name}'. Please check the parameters and try again."


if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=8081, path="/mcp")
