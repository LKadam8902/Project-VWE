import asyncio
import os
import traceback
from pathlib import Path
import gradio as gr

from agents.orchestrator import Orchestrator 
from agents.team import Team
from utils import (
    extract_localhost_url,
    generate_workspace_zip,
    format_board_progress,
    reset_conversation
)

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", BASE_DIR / "workspace"))
SERVER_HOST = os.environ.get("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "7861"))

WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

OPEN_TAB_JS = """
(url) => {
    if (url && url.length > 0) {
        console.log("Opening dynamic server URL:", url);
        window.open(url, '_blank');
    }
}
"""

async def gemini_chat_pipeline(user_message: str, history: list):
    """Handles the Gemini-style streaming chat execution using dict messages format."""
    cleaned_goal = user_message.strip()
    if not cleaned_goal:
        yield history, "", None, ""
        return

    history.append({"role": "user", "content": cleaned_goal})
    history.append({"role": "assistant", "content": "🤔 **Thinking & Planning workflow...**"})
    yield history, "", None, ""

    try:
        team = Team()
        orchestrator = Orchestrator(team)
        execution_task = asyncio.create_task(orchestrator.execute(cleaned_goal))
        
        detected_url = ""
        
        # Stream live progress updates into the Gemini chat block
        while not execution_task.done():
            progress_md = format_board_progress()
            
            bot_content = f"""<details open>
<summary><b>🛠️ Agent Thinking & Working Process</b></summary>

{progress_md}

</details>

*Executing steps in workspace environment...*
"""
            history[-1] = {"role": "assistant", "content": bot_content}
            yield history, "", None, ""
            await asyncio.sleep(0.8)

        result = await execution_task
        result_str = str(result)
        
 
        zip_file_path = generate_workspace_zip()
        
      
        detected_url = extract_localhost_url(result_str)
        final_progress = format_board_progress()
        
        server_notice = f"\n\n🚀 **Local server started at:** [{detected_url}]({detected_url})" if detected_url else ""
        
        bot_final_content = f"""<details>
<summary><b>✅ Completed Agent Execution Steps</b></summary>

{final_progress}

</details>

### 🎯 Result
{result_str}
{server_notice}

📦 *Workspace project files have been zipped and are ready for download below.*
"""
        history[-1] = {"role": "assistant", "content": bot_final_content}
        
        yield history, "", zip_file_path if zip_file_path else None, detected_url

    except Exception as e:
        traceback.print_exc() 
        history[-1] = {"role": "assistant", "content": f"❌ **An error occurred during execution:**\n```\n{str(e)}\n```"}
        yield history, "", None, ""



custom_css = """
footer { display: none !important; }
"""

with gr.Blocks(title="BuildIT - Gemini Workspace UI") as demo:
    gr.Markdown("# ✨ BuildIT Agentic Studio")

    with gr.Row():
        with gr.Column(scale=4):
            chatbot = gr.Chatbot(
                label="Gemini Assistant",
                height=550
            )
            
            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="Ask the agent team to build a project (e.g., Build a FastAPI Todo App with SQLite)...",
                    container=False,
                    scale=5
                )
                submit_btn = gr.Button("Send ✨", variant="primary", scale=1)

            with gr.Row():
                clear_btn = gr.Button("🗑️ Reset Chat & Board", size="sm")

        with gr.Column(scale=2):
            gr.Markdown("### 📦 Workspace Artifacts")
            download_zip = gr.File(label="Generated Project Archive (.zip)", interactive=False)
            
            gr.Markdown("### 🌐 Dynamic Local Server")
            server_url_display = gr.Textbox(label="Active Local URL", interactive=False)

   
    auto_url_trigger = gr.Textbox(visible=False)

    submit_event = submit_btn.click(
        fn=gemini_chat_pipeline,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input, download_zip, auto_url_trigger]
    )
    
    msg_input.submit(
        fn=gemini_chat_pipeline,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input, download_zip, auto_url_trigger]
    )

   
    submit_event.then(
        fn=None,
        inputs=[auto_url_trigger],
        js=OPEN_TAB_JS
    )

    clear_btn.click(
        fn=reset_conversation,
        inputs=[],
        outputs=[chatbot, download_zip, auto_url_trigger]
    )

if __name__ == "__main__":
    demo.queue()
    demo.launch(
        server_name=SERVER_HOST, 
        server_port=SERVER_PORT,
        theme=gr.themes.Soft(),
        css=custom_css
    )