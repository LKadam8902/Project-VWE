import asyncio
from agents.team import Team
from agents.orchestrator import Orchestrator
import board

async def main():
    team = Team()
    
    orchestrator=Orchestrator(team)

    print("Building team and initializing SQLite board...")

    goal = "Create a simple FastAPI backend for task management."
    await orchestrator.setup(goal)
    print(f"\nProcessing goal: '{goal}'...\n")

    try:
        results = await orchestrator.execute(goal)
        
        print("\n--- FINAL BOARD VISUALIZATION ---")
        board.show_board()
    finally:
        await team.cleanup()

if __name__ == "__main__":
    asyncio.run(main())