# SPDX-License-Identifier: MIT
# man-which-tool: an MCP server that registers/manages man pages as resources

import concurrent.futures
import os
import subprocess
import time

from fastmcp.resources.resource import Resource
from mcp.server.fastmcp import FastMCP

# ----------------------
# Resource Classes
# ----------------------

class ManPageResource(Resource):
    content: str

    async def read(self) -> str:
        return self.content

class PathCommandsResource(Resource):
    async def read(self) -> str:
        commands = set()
        for cmds in _last_path_commands.values():
            commands.update(cmds)
        return "\n".join(sorted(commands)) if commands else "No commands loaded. Please run register_command_resource_tool first."

# ----------------------
# Global State
# ----------------------

_last_path_commands = {}

# ----------------------
# Server Initialization
# ----------------------

mcp = FastMCP("Man Which Tool Server", version="0.0.1")

# ----------------------
# Prompt Definitions
# ----------------------

@mcp.prompt()
def mwt_guide() -> str:
    return (
        "Welcome to the Man Which Tool server!\n\n"
        "This server exposes the following capabilities for managing and accessing man pages of system commands as MCP resources:\n"
        "- Register a man page by extracting it from the system (create_manpage_file).\n"
        "- Register a man page from an existing file (register_manpage_resource).\n"
        "- Check if a command exists in your PATH (is_command_available).\n"
        "- List all available commands in PATH as a resource (register_command_resource_tool and read_all_commands_resource).\n"
        "- Generate man pages for all commands in PATH in parallel (create_all_manpage_files).\n\n"
        "To register a single man page, use the `create_manpage_file` function with the command name (e.g., 'grep').\n"
        "To register an already-extracted man page file, use `register_manpage_resource` with the command name.\n"
        "To discover whether a command is installed, use `is_command_available` with the command name.\n"
        "To list all commands as a resource, run `register_command_resource_tool` and then `read_all_commands_resource`.\n"
        "To generate man pages for all commands at once, run `create_all_manpage_files`."
    )

@mcp.prompt()
def mwt_discovery_helper() -> str:
    return (
        "Server Capabilities:\n"
        "- MCP Tools (functions):\n"
        "  • create_manpage_file(command_name): Extract a man page from the system and register it as a resource.\n"
        "  • register_manpage_resource(command_name): Load and register a man page from an existing file.\n"
        "  • is_command_available(command_name): Check if a shell command exists in your PATH.\n"
        "  • register_command_resource_tool(): Refresh and register the list of all commands as a resource (man://all-tools).\n"
        "  • create_all_manpage_files(): Generate and register man pages for all commands in your PATH in parallel.\n"
        "  • read_manpage_resource(command_identifier): Read content of a registered man page resource by command name or URI.\n"
        "  • read_all_commands_resource(): Read and return the list of all commands registered as a resource.\n"
        "- Prompts (user guidance):\n"
        "  • mwt_guide: Overview and usage instructions.\n"
        "  • mwt_discovery_helper: This capability listing.\n"
        "  • mwt_path_commands_workflow: How to check command availability.\n"
        "  • mwt_create_all_manpage_files_workflow: How to generate all man pages.\n"
        "- Resources:\n"
        "  • ManPageResource (man://{command_name}): Individual man page.\n"
        "  • PathCommandsResource (man://all-tools): List of all executable commands in PATH.\n"
    )

@mcp.prompt()
def mwt_path_commands_workflow() -> str:
    return (
        "Workflow: Checking Command Availability\n"
        "1. Run `register_command_resource_tool` to refresh the list of commands.\n"
        "2. Use `is_command_available` with a command name to verify if it exists.\n"
        "3. If you install new software or change PATH, run `register_command_resource_tool` again to update."
    )

@mcp.prompt()
def mwt_create_all_manpage_files_workflow() -> str:
    return (
        "Workflow: Generating All Man Pages in Parallel\n"
        "1. Run `register_command_resource_tool` to ensure command list is current.\n"
        "2. Execute `create_all_manpage_files` to extract and register man pages for every command in PATH.\n"
        "3. Monitor logs or output for any commands that failed to generate.\n"
    )


# ----------------------
# Helper Functions
# ----------------------

def find_all_commands() -> dict[str, list[str]]:
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


def _process_command(command_name: str, existing_manpages: set[str]) -> tuple[str, bool, str]:
    try:
        if command_name in existing_manpages:
            register_manpage_resource(command_name)
            return (command_name, True, "")
        else:
            result = create_manpage_file(command_name)
            if result.startswith("Man page for") and "saved to" in result:
                return (command_name, True, "")
            else:
                return (command_name, False, result)
    except Exception as e:
        return (command_name, False, str(e))

# ----------------------
# MCP Tools
# ----------------------

@mcp.tool()
def register_command_resource_tool() -> dict:
    global _last_path_commands
    _last_path_commands = find_all_commands()
    resource = PathCommandsResource(
        uri="man://all-tools",
        name="All available commands in PATH",
        description="Commands found in the system's PATH.",
        mime_type="text/plain",
        tags={"man", "all-tools"},
    )
    mcp.add_resource(resource)
    return _last_path_commands

@mcp.tool()
def is_command_available(command_name: str) -> bool:
    register_command_resource_tool()
    all_commands = set()
    for cmds in _last_path_commands.values():
        all_commands.update(cmds)
    return command_name in all_commands

@mcp.tool()
def create_manpage_file(command_name: str) -> str:
    os.makedirs("manpages", exist_ok=True)
    path = f"manpages/{command_name}.txt"
    try:
        result = subprocess.run(
            ["man", command_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        col = subprocess.run(
            ["col", "-b"],
            input=result.stdout,
            stdout=subprocess.PIPE,
            check=True,
        )
        with open(path, "wb") as f:
            f.write(col.stdout)
        registration_message = register_manpage_resource(command_name)
        return f"Man page for {command_name} saved to {path}. {registration_message}"
    except subprocess.CalledProcessError as e:
        return f"Failed to extract man page for {command_name}: {e.stderr.decode().strip()}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def register_manpage_resource(command_name: str) -> str:
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

@mcp.tool()
def create_all_manpage_files() -> dict:
    # NOTE: "create_all_manpage_files" runs parallel threads that each call "register_manpage_resource", which calls "mcp.add_resource".
    # If "mcp.add_resource" or the underlying MCP implementation is not thread-safe, this could cause race conditions or missing registrations.
    # In that case, consider collecting all resource payloads in threads and invoking "mcp.add_resource" sequentially in the main thread instead.
    start_time = time.time()
    register_command_resource_tool()

    os.makedirs("manpages", exist_ok=True)
    existing_manpages = {fname[:-4] for fname in os.listdir("manpages") if fname.endswith(".txt")}

    commands = set()
    for cmds in _last_path_commands.values():
        commands.update(cmds)

    created = []
    errors = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(_process_command, cmd, existing_manpages): cmd for cmd in sorted(commands)}
        for future in concurrent.futures.as_completed(futures):
            cmd = futures[future]
            try:
                name, success, error_msg = future.result()
                if success:
                    created.append(cmd)
                else:
                    errors.append({"command": cmd, "error": error_msg})
            except Exception as e:
                errors.append({"command": cmd, "error": str(e)})

    end_time = time.time()
    duration = end_time - start_time
    print(f"create_all_manpage_files execution time with parallelism: {duration:.2f} seconds")

    return {"created": created, "errors": errors}

@mcp.tool()
async def read_manpage_resource(command_identifier: str) -> str:
    cmd = command_identifier.strip()
    uri = cmd if cmd.startswith("man://") else f"man://{cmd}"

    try:
        results = await mcp.read_resource(uri)
        for result in results:
            return result.content
        return f"No content found for resource '{uri}'."
    except Exception as e:
        return f"Error reading resource '{uri}': {e}"

@mcp.tool()
async def read_all_commands_resource() -> str:
    uri = "man://all-tools"
    try:
        results = await mcp.read_resource(uri)
        for result in results:
            return result.content
        return f"No content found for resource '{uri}'."
    except Exception as e:
        return f"Error reading resource '{uri}': {e}"

# ----------------------
# Server Runner
# ----------------------

if __name__ == "__main__":
    mcp.run()
