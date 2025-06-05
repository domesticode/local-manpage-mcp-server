from mcp.server.fastmcp import FastMCP
from fastmcp.resources.resource import Resource


class SimpleResource(Resource):
    content: str

    async def read(self) -> str:
        return self.content

# Create an MCP server
mcp = FastMCP("Weather Service")

# Tool implementation
@mcp.tool()
def get_weather(location: str) -> str:
    """Get the current weather for a specified location."""
    return f"Weather in {location}: Sunny, 72°F"

@mcp.tool()
def add_dynamic_resource(topic: str) -> str:
    """Dynamically add a text resource with given topic."""
    uri = f"text://{topic}"
    resource = SimpleResource(
        uri=uri,
        name=f"Dynamic {topic}",
        description=f"Dynamically generated resource for {topic}",
        mime_type="text/plain",
        tags={"dynamic", topic},
        content=f"Dynamic resource for {topic}!",
    )
    mcp.add_resource(resource)
    print(f"MCP: Added dynamic resource for {topic}")
    return f"Resource {uri} added."

# Resource implementation
@mcp.resource("weather://{location}")
def weather_resource(location: str) -> str:
    """Provide weather data as a resource."""
    return f"Weather data for {location}: Sunny, 72°F"

# Prompt implementation
@mcp.prompt()
def weather_report(location: str) -> str:
    """Create a weather report prompt."""
    return f"""You are a weather reporter. Weather report for {location}?"""


# Run the server
if __name__ == "__main__":
    mcp.run()