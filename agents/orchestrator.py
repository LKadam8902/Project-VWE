import json
from typing import Any, Dict
from agents import prompts
from dotenv import load_dotenv
from agents.team import Team
from deepagents import create_deep_agent
import board
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_core.tools import tool

import board


load_dotenv(override=True)

MODEL = "baseten:deepseek-ai/DeepSeek-V4-Pro-0813"


def create_orchestrator_tools(team: Team, goal_id: int):
    """Creates tool wrappers for the Orchestrator to delegate tasks and track progress on SQLite board."""

    @tool
    async def run_designer(objective: str) -> str:
        """Triggers the System Designer agent to generate technical design specifications."""
        step_id = board.add_step(goal_id, f"designer: {objective}" , role="designer")
        board.claim_todo(step_id)

        config = {"configurable": {"thread_id": f"designer_task_{step_id}"}}
        res = await team.agents["designer"].ainvoke(
            {"messages": [{"role": "user", "content": objective}]},
            config=config,
        )
        output = res["messages"][-1].content
        print(output)
        board.complete_todo(step_id, output)
        return f"Designer completed Step #{step_id}:\n{output}"

    @tool
    async def run_backend(objective: str) -> str:
        """Triggers the Backend Engineer agent. Automatically includes the latest design spec from the board."""
        design_spec = board.get_latest_result_by_role("designer")
        if not design_spec:
            return "Error: Cannot run backend without a completed design spec on the board. Call run_designer first."

        step_id = board.add_step(goal_id, f"backend: {objective}",role="backend")
        board.claim_todo(step_id)

        prompt = f"Design Spec Context:\n{design_spec}\n\nBackend Task:\n{objective}"
        config = {"configurable": {"thread_id": f"backend_task_{step_id}"}}
        res = await team.agents["backend"].ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
        )
        output = res["messages"][-1].content
        print(output)
        board.complete_todo(step_id, output)
        return f"Backend Engineer completed Step #{step_id}:\n{output}"

    @tool
    async def run_frontend(objective: str) -> str:
        """Triggers the Frontend Engineer agent. Automatically incorporates design specs and backend output."""
        design_spec = board.get_latest_result_by_role("designer")
        backend_output = board.get_latest_result_by_role("backend")

        if not backend_output:
            return "Error: Cannot run frontend without backend output on the board. Call run_backend first."

        step_id = board.add_step(goal_id, f"frontend: {objective}",role="frontend")
        board.claim_todo(step_id)

        prompt = (
            f"Design Spec Context:\n{design_spec}\n\n"
            f"Backend Spec Context:\n{backend_output}\n\n"
            f"Frontend Task:\n{objective}"
        )
        config = {"configurable": {"thread_id": f"frontend_task_{step_id}"}}
        res = await team.agents["frontend"].ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
        )
        output = res["messages"][-1].content
        print(output)
        board.complete_todo(step_id, output)
        return f"Frontend Engineer completed Step #{step_id}:\n{output}"

    @tool
    async def run_qa_check(verification_scope: str) -> str:
        """Triggers the QA Engineer agent to inspect frontend/backend outputs for bugs or missing requirements."""
        frontend_output = board.get_latest_result_by_role("frontend")
        backend_output = board.get_latest_result_by_role("backend")

        if not frontend_output or not backend_output:
            return "Error: Cannot run QA check until both backend and frontend deliverables exist on the board."

        step_id = board.add_step(goal_id, f"qa: {verification_scope}",role="qa")
        board.claim_todo(step_id)

        prompt = (
            f"Backend Deliverables:\n{backend_output}\n\n"
            f"Frontend Deliverables:\n{frontend_output}\n\n"
            f"QA Verification Scope:\n{verification_scope}"
        )
        config = {"configurable": {"thread_id": f"qa_task_{step_id}"}}
        res = await team.agents["qa"].ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
        )
        output = res["messages"][-1].content
        print(output)
        board.complete_todo(step_id, output)
        return f"QA Engineer completed Step #{step_id}:\n{output}"

    @tool
    def get_board_status() -> str:
        """Reads all todos, statuses, and completed results currently saved on the SQLite board."""
        todos = board.list_todos()
        print(todos)
        return json.dumps(todos, indent=2)

    return [run_designer, run_backend, run_frontend, run_qa_check, get_board_status]


class Orchestrator:

    def __init__(self, team: Team) -> None:
        self.team = team
        self.orchestrator_agent = None
        self.goal_id = None

    async def setup(self, goal: str) -> None:
        """Initializes the team, registers the top-level goal on SQLite board, and creates the orchestrator agent."""
        await self.team.build_team(reset_db=True)
        self.goal_id = board.add_goal(goal)

        tools = create_orchestrator_tools(self.team, self.goal_id)

        self.orchestrator_agent = create_deep_agent(
            model=MODEL,
            tools=tools,
            system_prompt=prompts.orchestrator_prompt,
            middleware=[ModelCallLimitMiddleware(run_limit=25)],
        )

    async def execute(self, goal: str) -> Dict[str, Any]:
        """Executes the orchestrator decision-making loop."""
        if not self.orchestrator_agent:
            await self.setup(goal)

        response = await self.orchestrator_agent.ainvoke(
            {"messages": [{"role": "user", "content": f"Project Goal: {goal}"}]}
        )

        print(response)

        return {
            "summary": response["messages"][-1].content,
            "board_todos": board.list_todos(),
        }