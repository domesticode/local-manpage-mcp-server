from mcp.server.fastmcp import FastMCP
from fastmcp.resources.resource import Resource
import os

class ManPageResource(Resource):
    content: str

    async def read(self) -> str:
        return self.content


# Create an MCP server
mcp = FastMCP("Man Which Tool Server", version="0.0.1")

@mcp.tool()
def populate_manpage_resource(tool: str) -> str:
    """
    Load the man page for the given tool and register it as a resource.
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
    
# Prompt implementation
@mcp.prompt()
def mwt_guide() -> str:
    """Server Guide"""
    return f"""You are a Man Which Tool user. The server exposes man pages as resources for various tools. 
    You need to run the tool `populate_manpage_resource` to load before the resources are available."""

@mcp.prompt()
def mwt_discovery_helper() -> str:
    """Server discovery"""
    return f"""List all available MCP capabilities of the Man which Tool server. Capabilities are Tools, Prompts, Resources and Sampling.
    Resources are added dynamically, which means resource discovery will vary based on the tools available in $PATH and the execution of the `populate_manpage_resource` tool."""

# Run the server
if __name__ == "__main__":
    mcp.run()