# man-which-tool
A MCP server which loads the man pages of tools in $PATH as resource. The goal is to provide the LLM with context of the commands on the host machine

## Starting the server
```
uv run mcp dev server.py
```


## helper

```
# make sure the manpages directory exists.
# col -b strips out backspaces and formatting for clean text.
man grep | col -b > manpages/grep.txt
```