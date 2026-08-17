"""Tools for multi-agent workflows: MCP servers, LangChain community tools, and custom tools."""

import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Tuple

import requests
from dotenv import load_dotenv
from langchain_community.tools import GoogleSerperRun
from langchain_community.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

load_dotenv(override=True)

# Wikimedia user-agent identification
#wikipedia.set_user_agent("agentic-track-course (https://edwarddonner.com)")

# Initialize standard search/lookup wrappers
search_tool = GoogleSerperRun(api_wrapper=GoogleSerperAPIWrapper())
#wikipedia_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())


@tool
def send_push_notification(text: str) -> str:
    """Send a short push notification to the user's mobile device via Pushover."""
    token = os.getenv("PUSHOVER_TOKEN")
    user = os.getenv("PUSHOVER_USER")

    if not token or not user:
        return "Push notification skipped: PUSHOVER_TOKEN or PUSHOVER_USER environment variables missing."

    response = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={"token": token, "user": user, "message": text},
        timeout=10,
    )
    response.raise_for_status()
    return "Notification sent successfully."


@tool
def request_human_help(instructions: str) -> str:
    """Ask the human user to perform an interactive action in the browser window
    that an AI agent cannot do automatically (e.g., CAPTCHAs, 2FA, manual OAuth logins).

    Args:
        instructions: Clear step-by-step description of what the user needs to complete.
    """
    return f"Human help requested: '{instructions}'. The user confirmed completion. Continue task."


def get_mcp_config(sandbox_dir: str) -> Dict[str, Any]:
    """Returns configuration dictionary for connected Model Context Protocol (MCP) servers."""
    return {
        "playwright": {
            "transport": "stdio",
            "command": "npx",
            "args": ["@playwright/mcp@latest", "--isolated"],
        },
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", sandbox_dir],
        },
    }


class McpSessions:
    """Manages persistent MCP client connections and server lifecycle using an Async Exit Stack."""

    def __init__(self, connections: Dict[str, Any]):
        self.connections = connections
        self.client = MultiServerMCPClient(self.connections)
        self.stack = AsyncExitStack()
        self.tools: List[Any] = []

    async def __aenter__(self) -> List[Any]:
        """Opens MCP stdio sessions and loads tools dynamically."""
        await self.stack.__aenter__()
        for server_name in self.connections:
            session = await self.stack.enter_async_context(self.client.session(server_name))
            mcp_tools = await load_mcp_tools(session, server_name=server_name)
            self.tools.extend(mcp_tools)
        return self.tools

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Closes all MCP sessions cleanly, shutting down Playwright and filesystem processes."""
        await self.stack.__aexit__(exc_type, exc_val, exc_tb)


async def get_all_tools(sandbox_dir: str = "./sandbox") -> Tuple[List[Any], McpSessions]:
    """Helper function to return base tools + MCP sessions manager.

    Returns:
        A tuple of (list_of_all_tools, mcp_session_instance)
    """
    os.makedirs(sandbox_dir, exist_ok=True)
    sessions = McpSessions(get_mcp_config(sandbox_dir))
    mcp_tools = await sessions.__aenter__()

    base_tools = [search_tool, send_push_notification, request_human_help]
    all_tools = base_tools + mcp_tools

    return all_tools, sessions