from mcp.server.fastmcp import FastMCP
from fastmcp.resources.resource import Resource
import os
import subprocess
import time
import concurrent.futures

class ManPageResource(Resource):
    content: str

    async def read(self) -> str:
        return self.content

# Create an MCP server
mcp = FastMCP("Man Which Tool Server", version="0.0.1")

# Tool to load a man page file and register it as a resource (exposed for demo purposes)
@mcp.tool()
def populate_manpage_resource(command_name: str) -> str:
    """
    Load the man page for the given command from manpages/{command_name}.txt and register it as a resource.
    """
    path = f"manpages/{command_name}.txt"
    if os.path.exists(path):
        with open(path, "r") as f:
            content = f.read()
        resource = ManPageResource(
            uri=f"man://{command_name}",
            name=f"Man page for {command_name}",
            description=f"Manual page for {command_name}",
            mime_type="text/plain",
            tags={"man", command_name},
            content=content,
        )
        mcp.add_resource(resource)
        print(f"MCP: Loaded man page for {command_name}")
        return f"Man page for {command_name} loaded and registered."
    else:
        print(f"Man page for {command_name} not found at {path}")
        return f"Man page for {command_name} not found at {path}."

# Main entrypoint tool: extract and register a man page in one step
@mcp.tool()
def create_manpage_file(command_name: str) -> str:
    """
    Extract the man page for the given command and save it as manpages/{command_name}.txt.
    If successful, also register it as a resource.
    """
    os.makedirs("manpages", exist_ok=True)
    path = f"manpages/{command_name}.txt"
    try:
        # Run 'man command_name | col -b'
        result = subprocess.run(
            ["man", command_name],
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
        registration_message = populate_manpage_resource(command_name)
        return f"Man page for {command_name} saved to {path}. {registration_message}"
    except subprocess.CalledProcessError as e:
        return f"Failed to extract man page for {command_name}: {e.stderr.decode().strip()}"
    except Exception as e:
        return f"Error: {e}"

@mcp.prompt()
def mwt_guide() -> str:
    return (
        "Welcome to the Man Which Tool server!\n\n"
        "This server exposes man pages for commands available on your system as resources. "
        "To add a man page as a resource, use the `create_manpage_file` function with the command name (e.g., 'grep'). "
        "This will extract the man page, save it to the manpages directory, and register it as a resource.\n\n"
        "For demonstration purposes, you can also use the `populate_manpage_resource` function to register a man page "
        "from an existing file in the manpages directory.\n\n"
        "Once registered, man pages are available as resources (e.g., man://grep) for LLMs and clients to access."
    )

@mcp.prompt()
def mwt_discovery_helper() -> str:
    return (
        "Capabilities of the Man Which Tool server:\n"
        "- Functions (MCP tools):\n"
        "  • create_manpage_file(command_name): Extract and register a man page as a resource.\n"
        "  • populate_manpage_resource(command_name): Register a man page from an existing file.\n"
        "  • is_command_available(command_name): Check if a command exists in your PATH.\n"
        "  • create_all_manpages(): Generate man pages for all available commands.\n"
        "- Prompts:\n"
        "  • mwt_guide: Overview and usage instructions.\n"
        "  • mwt_discovery_helper: This capability listing.\n"
        "- Resources:\n"
        "  • Man pages registered as resources (e.g., man://grep).\n"
        "\n"
        "To discover available commands, check your system's $PATH or use `populate_command_resource_tool`."
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

# Dynamic resource: list of all available commands in PATH (from last list_path_commands call)
class PathCommandsResource(Resource):
    async def read(self) -> str:
        commands = set()
        for cmds in _last_path_commands.values():
            commands.update(cmds)
        return "\n".join(sorted(commands)) if commands else "No commands loaded. Please run populate_command_resource_tool first."

# Tool: Check if a command is available in PATH (from last list_path_commands call)
@mcp.tool()
def is_command_available(command_name: str) -> bool:
    """
    Check if the given command is available in the system's PATH.
    Returns True if available, False otherwise.
    Uses the last result from populate_command_resource_tool.
    """
    populate_command_resource_tool()
    all_commands = set()
    for cmds in _last_path_commands.values():
        all_commands.update(cmds)
    return command_name in all_commands

@mcp.prompt()
def mwt_path_commands_workflow() -> str:
    return (
        "To check if a command is available in your system's PATH, use the `is_command_available` function. "
        "If you have installed new commands or modified your PATH, run `populate_command_resource_tool` again to refresh the list."
    )

@mcp.prompt()
def mwt_create_all_manpages_workflow() -> str:
    """Workflow for creating all manpages"""
    return (
        "To create manpages for all commands, run the `create_all_manpages` tool. "
        "This will automatically populate the command resource and then generate manpages for all commands that do not already have one."
    )

# Helper function to process a single command
def _process_command(command_name: str, existing_manpages: set) -> tuple[str, bool, str]:
    """
    Process an individual command: if a manpage exists, register it; otherwise, create it.
    Returns (command_name, success, error_message).
    """
    try:
        if command_name in existing_manpages:
            populate_manpage_resource(command_name)
            return (command_name, True, "")
        else:
            result = create_manpage_file(command_name)
            if result.startswith("Man page for") and "saved to" in result:
                return (command_name, True, "")
            else:
                return (command_name, False, result)
    except Exception as e:
        return (command_name, False, str(e))

@mcp.tool()
def create_all_manpages() -> dict:
    """
    Create manpages for all commands in the current PathCommandsResource using parallel execution.
    Skips commands that already have a manpage file, but still registers them.
    Returns a summary dict with 'created', 'skipped', and 'errors'.
    """
    start_time = time.time()
    # Refresh command list
    populate_command_resource_tool()

    # Ensure manpages directory exists
    os.makedirs("manpages", exist_ok=True)
    existing_manpages = {fname[:-4] for fname in os.listdir("manpages") if fname.endswith(".txt")}

    # Gather all unique commands
    commands = set()
    for cmds in _last_path_commands.values():
        commands.update(cmds)

    created = []
    skipped = []
    errors = []

    # Use ThreadPoolExecutor for parallel IO-bound tasks
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(_process_command, cmd, existing_manpages): cmd for cmd in sorted(commands)}
        for future in concurrent.futures.as_completed(futures):
            cmd = futures[future]
            success = False
            try:
                name, success, error_msg = future.result()
            except Exception as e:
                success = False
                error_msg = str(e)
            if success:
                created.append(cmd)
            else:
                errors.append({"command": cmd, "error": error_msg})

    end_time = time.time()
    duration = end_time - start_time
    print(f"create_all_manpages execution time with parallelism: {duration:.2f} seconds")

    return {"created": created, "skipped": skipped, "errors": errors}

# Command to read and return the content of a registered manpage resource given its URI
@mcp.tool()
async def read_manpage_resource(command_identifier: str) -> str:
    """
    Asynchronously read and return the content of a registered manpage resource for the given command name or URI.
    If the input is already a URI (starts with 'man://'), use it directly; otherwise, assemble as man://{command_identifier}.
    Returns an error message if the resource is not found or not readable.
    """
    cmd = command_identifier.strip()
    if cmd.startswith("man://"):
        uri = cmd
    else:
        uri = f"man://{cmd}"

    try:
        results = await mcp.read_resource(uri)
        for result in results:
            return result.content
        return f"No content found for resource '{uri}'."
    except Exception as e:
        return f"Error reading resource '{uri}': {e}"

@mcp.tool()
async def read_all_commands_resource() -> str:
    """
    Asynchronously read and return the content of the resource listing all available commands (man://all-tools).
    Returns an error message if the resource is not found or not readable.
    """
    uri = "man://all-tools"
    try:
        results = await mcp.read_resource(uri)
        for result in results:
            return result.content
        return f"No content found for resource '{uri}'."
    except Exception as e:
        return f"Error reading resource '{uri}': {e}"

# Run the server
if __name__ == "__main__":
    mcp.run()
