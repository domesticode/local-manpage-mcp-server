# local-manpage-mcp-server

## Summary
`local-manpage-mcp-server` is an MCP server that extracts and exposes the man pages of all executables in your `$PATH` as MCP resources. Its primary goal is to give an LLM (or any MCP client) direct access to up-to-date documentation for the commands installed on the host. This server is intended to run on Linux distributions only (see **Disclaimer** below).

create_all_manpage_files creates the manpages directory in which the manpages are stored. Those files are read when requesting the resource. There is also a wrapper tool in case you host application does not support MCP resources.

## Disclaimer
Linux Only: This server is designed exclusively for Linux distributions. It relies on the `man` and `col` utilities (and a standard $PATH structure) to extract man pages. It has not been tested on macOS, BSD, or Windows, and may not function correctly elsewhere.

Permissions: You must have read access to all directories in your $PATH and write permission to a local manpages/ folder (created automatically).

Resource Limits: Generating man pages for a large number of binaries can be CPU‐ and disk‐intensive.

Argument Safety: The arguments passed to `man` and `col` are not sanitized or validated, which could potentially allow command‐injection if malicious input is provided.

## Setup
```bash
   git clone https://github.com/yourusername/local-manpage-mcp-server.git
   cd local-manpage-mcp-server

   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
```

## Starting the MCP Server and Inspector

```
uv run mcp dev server.py
```

## Usage
One goal was to create a self-explanatory server which provides the Usage as prompt for your host application, so you should be able to let you LLM explain the workflow.

Appart from that, the server needs to create the MCP resources based on your systems commands by running the tool `create_all_manpage_files`. After the execution all manpages should be available as MCP resource.

