from mcp.server.fastmcp import FastMCP
from fastmcp.resources.resource import Resource
import os
import subprocess

class ManPageResource(Resource):
    content: str

    async def read(self) -> str:
        return self.content

# Create an MCP server
mcp = FastMCP("Man Which Tool Server", version="0.0.1")

# Tool to load a man page file and register it as a resource (exposed for demo purposes)
@mcp.tool()
def populate_manpage_resource(tool: str) -> str:
    """
    Load the man page for the given tool from manpages/{tool}.txt and register it as a resource.
    """
    path = f"manpages/{tool}.txt"
    if os.path.exists(path):
        with open(path, "r") as f:
            content = f.read()
        resource = ManPageResource(
            uri=f"man://{tool}",
            name=f"Man page for {tool}",
            description=f"Manual page for {tool}",
            mime_type="text/plain",
            tags={"man", tool},
            content=content,
        )
        mcp.add_resource(resource)
        print(f"MCP: Loaded man page for {tool}")
        return f"Man page for {tool} loaded and registered."
    else:
        print(f"Man page for {tool} not found at {path}")
        return f"Man page for {tool} not found at {path}."

# Main entrypoint tool: extract and register a man page in one step
@mcp.tool()
def create_manpage_file(tool: str) -> str:
    """
    Extract the man page for the given tool and save it as manpages/{tool}.txt.
    If successful, also register it as a resource.
    """
    os.makedirs("manpages", exist_ok=True)
    path = f"manpages/{tool}.txt"
    try:
        # Run 'man tool | col -b'
        result = subprocess.run(
            ["man", tool],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        # Clean formatting with col -b
        col = subprocess.run(
            ["col", "-b"],
            input=result.stdout,
            stdout=subprocess.PIPE,
            check=True,
        )
        with open(path, "wb") as f:
            f.write(col.stdout)
        # Call populate_manpage_resource after successful file creation
        reg_msg = populate_manpage_resource(tool)
        return f"Man page for {tool} saved to {path}. {reg_msg}"
    except subprocess.CalledProcessError as e:
        return f"Failed to extract man page for {tool}: {e.stderr.decode().strip()}"
    except Exception as e:
        return f"Error: {e}"

# Guide prompt: updated to reflect current workflow
@mcp.prompt()
def mwt_guide() -> str:
    """Server Guide"""
    return (
        "Welcome to the Man Which Tool server!\n\n"
        "This server exposes man pages for tools available on your system as resources. "
        "To add a man page as a resource, use the `create_manpage_file` tool with the tool name (e.g., 'grep'). "
        "This will extract the man page, save it to the manpages directory, and register it as a resource.\n\n"
        "For demonstration purposes, you can also use the `populate_manpage_resource` tool to register a man page "
        "from an existing file in the manpages directory.\n\n"
        "Once registered, man pages are available as resources (e.g., man://grep) for LLMs and clients to access."
    )

# Discovery prompt: updated for clarity and completeness
@mcp.prompt()
def mwt_discovery_helper() -> str:
    """Server discovery"""
    return (
        "Capabilities of the Man Which Tool server:\n"
        "- Tools:\n"
        "  • create_manpage_file(tool): Extract and register a man page as a resource (recommended entrypoint).\n"
        "  • populate_manpage_resource(tool): Register a man page from an existing file (demo/advanced usage).\n"
        "- Prompts:\n"
        "  • mwt_guide: Overview and usage instructions.\n"
        "  • mwt_discovery_helper: This capability listing.\n"
        "- Resources:\n"
        "  • Man pages registered as resources (e.g., man://grep).\n"
        "\n"
        "To discover available tools, check your system's $PATH or try common utilities like 'ls', 'grep', or 'cat'."
    )

def populate_command_resource():
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    seen = set()
    all_commands = {}

    for dir_path in path_dirs:
        if os.path.isdir(dir_path):
            try:
                entries = os.listdir(dir_path)
            except PermissionError:
                continue  # Skip directories we can't access

            commands = []
            for entry in entries:
                full_path = os.path.join(dir_path, entry)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    if entry not in seen:
                        seen.add(entry)
                        commands.append(entry)

            if commands:
                all_commands[dir_path] = sorted(commands)

    return all_commands

# Store the last result of list_path_commands in a global variable
_last_path_commands = {}

@mcp.tool()
def populate_command_resource_tool() -> dict:
    """
    List all executable commands available in the system's PATH.
    Returns a dictionary mapping each PATH directory to a sorted list of unique executable names.
    Also updates the global _last_path_commands for use by other resources/tools.
    """
    global _last_path_commands
    _last_path_commands = populate_command_resource()
    # Register the dynamic resource after updating _last_path_commands
    resource = PathCommandsResource(
        uri="man://all-tools",
        name="All available tools in PATH",
        description="A list of all executable commands found in the system's PATH (populated by populate_command_resource_tool).",
        mime_type="text/plain",
        tags={"man", "all-tools"},
    )
    mcp.add_resource(resource)
    return _last_path_commands

# Dynamic resource: list of all available tools in PATH (from last list_path_commands call)
class PathCommandsResource(Resource):
    async def read(self) -> str:
        commands = set()
        for cmds in _last_path_commands.values():
            commands.update(cmds)
        return "\n".join(sorted(commands)) if commands else "No commands loaded. Please run populate_command_resource_tool first."

# Tool: Check if a tool is available in PATH (from last list_path_commands call)
@mcp.tool()
def is_tool_available(tool: str) -> bool:
    """
    Check if the given tool is available in the system's PATH.
    Returns True if available, False otherwise.
    Uses the last result from populate_command_resource_tool.
    """
    all_tools = set()
    for cmds in _last_path_commands.values():
        all_tools.update(cmds)
    return tool in all_tools

# Workflow prompt: explains the order of operations for checking tool availability
@mcp.prompt()
def mwt_path_commands_workflow() -> str:
    """Workflow for checking tool availability"""
    return (
        "To check if a tool is available in your system's PATH, first run the `populate_command_resource_tool` tool. "
        "This will scan your PATH and register all available commands. "
        "After that, you can use the `is_tool_available` tool to check if a specific tool is present. "
        "If you have installed new tools or changed your PATH, run `populate_command_resource_tool` again to refresh the list."
    )

@mcp.prompt()
def mwt_create_all_manpages_workflow() -> str:
    """Workflow for creating all manpages"""
    return (
        "To create manpages for all commands, first run the `populate_command_resource_tool` tool to populate the command resource. "
        "This ensures the list of commands is up to date. "
        "Then run the `create_all_manpages` tool to generate manpages for all commands that do not already have one."
    )

@mcp.tool()
def create_all_manpages() -> dict:
    """
    Create manpages for all commands in the current PathCommandsResource.
    Skips commands that already have a manpage file in manpages/{tool}.txt.
    Returns a summary dict with 'created', 'skipped', and 'errors'.
    """
    created = []
    skipped = []
    errors = []
    # Gather all unique commands from _last_path_commands
    commands = set()
    for cmds in _last_path_commands.values():
        commands.update(cmds)
    for tool in sorted(commands):
        path = f"manpages/{tool}.txt"
        if os.path.exists(path):
            skipped.append(tool)
            continue
        result = create_manpage_file(tool)
        if result.startswith("Man page for") and "saved to" in result:
            created.append(tool)
        else:
            errors.append({"tool": tool, "error": result})
    return {"created": created, "skipped": skipped, "errors": errors}

# Run the server
if __name__ == "__main__":
    mcp.run()