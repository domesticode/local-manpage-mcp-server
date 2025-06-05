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

# Run the server
if __name__ == "__main__":
    mcp.run()