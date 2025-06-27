from fastmcp.server import FastMCP
from typing import Annotated, Literal
from pydantic import Field
import os
import subprocess
import json
import re


SIMULATE_MODIFICATIONS = False

mcp = FastMCP()


@mcp.tool(
    name="list_inbound_firewall_rules",
    description="Lists all inbound firewall rules that are enabled and allow traffic. Returns a JSON array of objects with properties: 'Rule Name', 'Grouping', 'LocalPort', and 'Protocol'.",
    annotations={"title": "List Inbound Firewall Rules"},
)
def list_inbound_firewall_rules() -> str:
    try:
        out_bytes = subprocess.check_output(
            "netsh advfirewall firewall show rule name=all", shell=True
        )
        out_str = out_bytes.decode("utf-8").replace("Ok.", "")
        temp = [k for x in re.split(r"\n\s*\n", out_str) if (k := x.strip())]
        rule_lines = [
            {
                z[0].strip(): z[1].strip()
                for k in x.split("\n")
                if (y := k.strip())
                and not y.startswith("------")
                and len(z := y.split(": ", 1)) == 2
            }
            for x in temp
        ]

        filtered_rules = [
            rule
            for rule in rule_lines
            if rule.get("Enabled", "") == "Yes"
            and rule.get("Direction", "") == "In"
            and rule.get("Action", "") == "Allow"
        ]

        filtered_rules = [
            rule
            for rule in filtered_rules
            if not (
                (rname := rule.get("Rule Name", "")).startswith("@")
                or rname.startswith("{")
                or (rgroup := rule.get("Grouping", "")).startswith("@")
                or rgroup.startswith("{")
            )
        ]

        target_properties = ["Rule Name", "Grouping", "LocalPort", "Protocol"]
        final_rules = [
            {k: v for k, v in rule.items() if k in target_properties}
            for rule in filtered_rules
        ]
        return json.dumps(final_rules)
    except Exception as e:
        return f"Failed to list inbound firewall rules."

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
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command "
            f"New-NetFirewallRule -Name '{rule_name}' -DisplayName '{display_name}' "
            f"-Action {action} -LocalPort {local_port} -Protocol {protocol} -Direction {direction} -Enabled True"
        )
    if res == 0:
        return f"Firewall rule '{rule_name}' created successfully."
    else:
        return f"Failed to create firewall rule '{rule_name}'. Please check the parameters and try again."


@mcp.tool(
    name="disable_firewall_rule",
    description="Disables a firewall rule with the specified name.",
    annotations={"title": "Disable Firewall Rule"},
)
def disable_firewall_rule(
    rule_name: Annotated[
        str, Field(description="Name of the firewall rule to disable")
    ],
) -> str:
    print(f"Disabling firewall rule with name: {rule_name}")
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command "
            f"Set-NetFirewallRule -Name '{rule_name}' -Enabled False"
        )
    if res == 0:
        return f"Firewall rule '{rule_name}' disabled successfully."
    else:
        return f"Failed to disable firewall rule '{rule_name}'. Please check the parameters and try again."


@mcp.tool(
    name="get_job_descriptions",
    description="Returns a description of the available tools and their usage.",
    annotations={"title": "Get Job Descriptions"},
)
def get_job_descriptions() -> str:
    try:
        with open("context/job_descriptions.txt", "r") as file:
            descriptions = file.read()

        return descriptions
    except Exception:
        return "Failed to retrieve job descriptions."


"""
## ACTIVE DIRECTORY TOOLS
"""


@mcp.tool(
    name="list_constrained_delegation",
    description="Lists the 'AllowedToDelegate' permissions for an Active Directory account.",
    annotations={"title": "List Constrained Delegation"},
)
def list_constrained_delegation(
    identity: Annotated[
        str, Field(description="Account Identity (e.g., username or samAccountName)")
    ],
) -> str:
    print(f"Listing constrained delegation for account: {identity}")

    try:
        # Use subprocess to capture the output
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        result = subprocess.run(
            [
                "powershell.exe",
                "-Command",
                f"Get-ADUser -Identity '{identity}' -Properties msDS-AllowedToDelegateTo | "
                "Select-Object -ExpandProperty msDS-AllowedToDelegateTo",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse the output
        output = result.stdout.strip()
        if output:
            # Split by newlines and filter out empty lines
            spns = [line.strip() for line in output.split("\n") if line.strip()]
            if spns:
                spn_list = "\n".join([f"  - {spn}" for spn in spns])
                return (
                    f"Constrained delegation SPNs for account '{identity}':\n{spn_list}"
                )
            else:
                return f"No constrained delegation permissions found for account '{identity}'."
        else:
            return (
                f"No constrained delegation permissions found for account '{identity}'."
            )

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown error"
        return f"Failed to list constrained delegation for account '{identity}'. Error: {error_msg}"
    except Exception as e:
        return f"Failed to list constrained delegation for account '{identity}'. Error: {str(e)}"


@mcp.tool(
    name="remove_constrained_delegation",
    description="Removes the 'AllowedToDelegate' permission from an Active Directory account.",
    annotations={"title": "Add AD Group Member"},
)
def remove_constrained_delegation(
    identity: Annotated[
        str, Field(description="Account Identity (e.g., username or samAccountName)")
    ],
    target: Annotated[
        str,
        Field(
            description="Target service to remove from delegation (e.g. 'service/hostname' which is the SPN)"
        ),
    ],
) -> str:
    print(
        f"Removing constrained delegation for account with parameters:\n"
        f"Account: {identity}\n"
        f"Target: {target}"
    )
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command "
            f"Set-ADUser -Identity '{identity}' -Remove @{{'msDS-AllowedToDelegateTo'='{target}'}}"
        )
    if res == 0:
        return f"Removed constrained delegation for account '{identity}' targeting '{target}' successfully."
    else:
        return f"Failed to remove constrained delegation for account '{identity}' targeting '{target}'. Please check the parameters and try again."


@mcp.tool(
    name="add_ad_group_member",
    description="Adds a member to an Active Directory group.",
    annotations={"title": "Add AD Group Member"},
)
def add_ad_group_member(
    identity: Annotated[str, Field(description="Group Identity (e.g., group name)")],
    member: Annotated[
        str, Field(description="Member Identity to add (e.g., username)")
    ],
) -> str:
    print(
        f"Adding member to AD group with parameters:\n"
        f"Group: {identity}\n"
        f"Member: {member}"
    )
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command "
            f"Add-ADGroupMember -Identity '{identity}' -Members '{member}'"
        )
    if res == 0:
        return f"Added member '{member}' to group '{identity}' successfully."
    else:
        return f"Failed to add member '{member}' to group '{identity}'. Please check the parameters and try again."


@mcp.tool(
    name="remove_ad_group_member",
    description="Removes a member from an Active Directory group.",
    annotations={"title": "Remove AD Group Member"},
)
def remove_ad_group_member(
    identity: Annotated[str, Field(description="Group Identity (e.g., group name)")],
    member: Annotated[
        str, Field(description="Member Identity to remove (e.g., username)")
    ],
) -> str:
    print(
        f"Removing member from AD group with parameters:\n"
        f"Group: {identity}\n"
        f"Member: {member}"
    )
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command "
            f"Remove-ADGroupMember -Identity '{identity}' -Members '{member}' -Confirm:$false"
        )
    if res == 0:
        return f"Removed member '{member}' from group '{identity}' successfully."
    else:
        return f"Failed to remove member '{member}' from group '{identity}'. Please check the parameters and try again."


@mcp.tool(
    name="new_ad_user",
    description="Creates a new Active Directory user.",
    annotations={"title": "New AD User"},
)
def new_ad_user(
    name: Annotated[str, Field(description="User's full name (e.g., 'John Smith')")],
    sam_account_name: Annotated[
        str, Field(description="User's logon name (pre-Windows 2000)")
    ],
    password: Annotated[
        str,
        Field(
            description="The user's initial password. This will be set as an expired password, forcing the user to change it on next logon."
        ),
    ],
    enabled: Annotated[
        bool,
        Field(
            description="Whether the account should be enabled or disabled upon creation."
        ),
    ] = True,
) -> str:
    print(
        f"Creating new AD user with parameters:\n"
        f"Name: {name}\n"
        f"SAM Account Name: {sam_account_name}\n"
        f"Enabled: {enabled}"
    )
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # Note: Passing passwords directly can be a security risk.
        # This command sets the password and requires the user to change it at next logon.
        pw_command = f'$Password = ConvertTo-SecureString -String \\"{password}\\" -AsPlainText -Force'
        command = (
            f'{pw_command}; New-ADUser -Name "{name}" -SamAccountName "{sam_account_name}" '
            f"-AccountPassword $Password -Enabled ${str(enabled).lower()} -ChangePasswordAtLogon $true"
        )
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(f'powershell.exe -Command "{command}"')
    if res == 0:
        return f"AD user '{name}' created successfully."
    else:
        return f"Failed to create AD user '{name}'. Please check the parameters and try again."


@mcp.tool(
    name="remove_ad_user",
    description="Removes an Active Directory user.",
    annotations={"title": "Remove AD User"},
)
def remove_ad_user(
    identity: Annotated[
        str, Field(description="User Identity (e.g., username or distinguished name)")
    ],
) -> str:
    print(f"Removing AD user with identity: {identity}")
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command "
            f"Remove-ADUser -Identity '{identity}' -Confirm:$false"
        )
    if res == 0:
        return f"Removed user '{identity}' successfully."
    else:
        return f"Failed to remove user '{identity}'. Please check the parameters and try again."


@mcp.tool(
    name="disable_ad_account",
    description="Disables an Active Directory account.",
    annotations={"title": "Disable AD Account"},
)
def disable_ad_account(
    identity: Annotated[str, Field(description="Account Identity (e.g., username)")],
) -> str:
    print(f"Disabling AD account with identity: {identity}")
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command " f"Disable-ADAccount -Identity '{identity}'"
        )
    if res == 0:
        return f"Disabled account '{identity}' successfully."
    else:
        return f"Failed to disable account '{identity}'. Please check the parameters and try again."


@mcp.tool(
    name="enable_ad_account",
    description="Enables an Active Directory account.",
    annotations={"title": "Enable AD Account"},
)
def enable_ad_account(
    identity: Annotated[str, Field(description="Account Identity (e.g., username)")],
) -> str:
    print(f"Enabling AD account with identity: {identity}")
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command " f"Enable-ADAccount -Identity '{identity}'"
        )
    if res == 0:
        return f"Enabled account '{identity}' successfully."
    else:
        return f"Failed to enable account '{identity}'. Please check the parameters and try again."


@mcp.tool(
    name="set_ad_account_password",
    description="Resets the password for an Active Directory user account.",
    annotations={"title": "Reset AD Account Password"},
)
def set_ad_account_password(
    identity: Annotated[str, Field(description="Account Identity (e.g., username)")],
    new_password: Annotated[
        str, Field(description="The new password for the account.")
    ],
) -> str:
    print(f"Resetting password for AD account: {identity}")
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        pw_command = f'$Password = ConvertTo-SecureString -String \\"{new_password}\\" -AsPlainText -Force'
        command = (
            f'{pw_command}; Set-ADAccountPassword -Identity "{identity}" '
            f"-NewPassword $Password -Reset:$true"
        )
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(f'powershell.exe -Command "{command}"')
    if res == 0:
        return f"Password for account '{identity}' has been reset successfully."
    else:
        return f"Failed to reset password for account '{identity}'. Please check the parameters and try again."


@mcp.tool(
    name="new_ad_group",
    description="Creates a new Active Directory group.",
    annotations={"title": "New AD Group"},
)
def new_ad_group(
    name: Annotated[str, Field(description="Name for the new group")],
    group_scope: Annotated[
        Literal["DomainLocal", "Global", "Universal"],
        Field(description="Scope of the group"),
    ],
    group_category: Annotated[
        Literal["Security", "Distribution"], Field(description="Category of the group")
    ] = "Security",
) -> str:
    print(
        f"Creating new AD group with parameters:\n"
        f"Name: {name}\n"
        f"Scope: {group_scope}\n"
        f"Category: {group_category}"
    )
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command "
            f"New-ADGroup -Name '{name}' -GroupScope {group_scope} -GroupCategory {group_category}"
        )
    if res == 0:
        return f"AD group '{name}' created successfully."
    else:
        return f"Failed to create AD group '{name}'. Please check the parameters and try again."


@mcp.tool(
    name="remove_ad_group",
    description="Removes an Active Directory group.",
    annotations={"title": "Remove AD Group"},
)
def remove_ad_group(
    identity: Annotated[str, Field(description="Group Identity (e.g., group name)")],
) -> str:
    print(f"Removing AD group with identity: {identity}")
    if SIMULATE_MODIFICATIONS:
        res = 0
    else:
        # DISCLAIMER: Yes, we know what command injection is. Don't do this. This was hacked together quickly for demonstration purposes.
        res = os.system(
            "powershell.exe -Command "
            f"Remove-ADGroup -Identity '{identity}' -Confirm:$false"
        )
    if res == 0:
        return f"Removed group '{identity}' successfully."
    else:
        return f"Failed to remove group '{identity}'. Please check the parameters and try again."


if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=8081, path="/mcp")
