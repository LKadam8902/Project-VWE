import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from deepagents import create_deep_agent
import board
from agents import prompts
from tools import (
    get_all_tools,
    request_human_help,
    send_push_notification,
    search_tool,
)

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from deepagents.backends import FilesystemBackend

load_dotenv(override=True)

MODEL = "baseten:deepseek-ai/DeepSeek-V4-Pro-0813"
SANDBOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox")


class Team:

    def __init__(self, memory_checkpointer: Optional[Any] = None) -> None:
        """Initializes storage for agents, memory, active sessions, and board state."""
        self.agents: Dict[str, Any] = {}
        self.sessions: List[Any] = []
        self.memory = memory_checkpointer if memory_checkpointer is not None else MemorySaver()
        self.active_goal_id: Optional[int] = None

    async def build_team(self, reset_db: bool = True) -> Dict[str, Any]:
        """Loads tools, builds agent instances, and resets the SQLite board."""
        # Ensure sandbox directory exists
        os.makedirs(SANDBOX_DIR, exist_ok=True)

        # 1. Reset/Initialize SQLite Board
        if reset_db:
            board.reset_board()

        # 2. Retrieve all tools (Base + MCP Playwright & Filesystem)
        all_tools, mcp_sessions = await get_all_tools(SANDBOX_DIR)
        self.sessions = [mcp_sessions]

        # Separate MCP tools by server source for targeted assignment
        mcp_filesystem_tools = [t for t in all_tools if t.name.startswith("filesystem_")]
        mcp_browser_tools = [t for t in all_tools if t.name.startswith("playwright_")]

        # 3. Define role tool assignments
        role_tool_mapping = {
            "designer": [search_tool] + mcp_filesystem_tools,
            "backend": [search_tool] + mcp_filesystem_tools,
            "frontend": [search_tool, request_human_help] + mcp_browser_tools + mcp_filesystem_tools,
            "qa": [request_human_help, send_push_notification] + mcp_browser_tools + mcp_filesystem_tools,
        }

        agent_configs = {
            "designer": prompts.system_designer_prompt,
            "backend": prompts.backend_engineer_prompt,
            "frontend": prompts.frontend_engineer_prompt,
            "qa": prompts.test_engineer_prompt,
        }

        # 4. Instantiate agents
        for role, system_prompt in agent_configs.items():
            self.agents[role] = create_deep_agent(
                model=MODEL,
                tools=role_tool_mapping[role],
                system_prompt=agent_configs[role],
                checkpointer=self.memory,
                backend=FilesystemBackend(root_dir=".", virtual_mode=True)
            )

        return self.agents

    def monitor_team(self) -> Dict[str, Any]:
        """Prints rich terminal representation of the current SQLite board status."""
        board.show_board()
        return {role: f"Active ({len(agent.tools)} tools)" for role, agent in self.agents.items()}

    async def cleanup(self) -> None:
        """Clean up active MCP or background tool sessions cleanly."""
        for session in self.sessions:
            if hasattr(session, "close"):
                await session.close()
            elif hasattr(session, "__aexit__"):
                await session.__aexit__(None, None, None)