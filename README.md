# 🛠️ BuildIT — Agentic Engineering Sandbox

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Gradio](https://img.shields.io/badge/UI-Gradio_5.0%2B-orange.svg)](https://gradio.app/)
[![LangChain](https://img.shields.io/badge/Framework-LangChain-green.svg)](https://www.langchain.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **BuildIT** is an autonomous multi-agent software engineering studio. It coordinates specialized AI agents (System Designer, Backend Engineer, Frontend Engineer, and QA Tester) led by an Orchestrator to plan, build, test, and host end-to-end applications from a single natural language goal.

---

## 🚀 Live Demo & Artifacts

* **Live Interactive Workspace:** [https://buildit-agentic-studio.hf.space](https://buildit-agentic-studio.hf.space) *(Replace with your deployment link)*
* **Demo Video / Walkthrough:** [Watch on YouTube](https://youtube.com)

---

## 📸 Interface & Workflow Screenshots

### 1. Gemini-Style Chat UI & Live Thinking Process
> The interactive workspace streams execution progress, dynamic task board state, and sub-agent step outputs in real time.

![BuildIT Chat Interface](docs/images/chat-interface.png)

### 2. Autonomous Task Board Tracking
> Tasks are dynamically added, claimed, and updated across SQLite persistence tables as agents progress through requirements.

![Active Task Board](docs/images/task-board.png)

### 3. Generated Workspace Artifacts & Auto-Hosted Server
> Upon project completion, BuildIT bundles all generated source files into a downloadable ZIP archive and automatically spins up a local server preview.

![Workspace Artifacts](docs/images/workspace-artifacts.png)

---

## ✨ Key Features

* **🤖 Multi-Agent Collaboration:** Dedicated roles for System Architecture, Backend Development, Frontend UI, and QA Verification.
* **⚡ Live Agent Thinking Blocks:** Collapsible, real-time agent execution step updates embedded directly in the chat pipeline.
* **💾 Automatic File Generation & Zip Export:** Automatically aggregates workspace outputs into an organized downloadable project archive (`workspace.zip`).
* **🌐 Dynamic Local App Hosting:** Detects and launches live local server previews (`http://127.0.0.1:7861`) directly in a new browser tab.
* **📊 SQLite Task Board Persistence:** Tracks task dependencies, execution state (`done`, `in_progress`, `pending`), and role outputs cleanly.

---

## 📐 System Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    User Interface                       │
│              (Gradio 5.0 Gemini-Style UI)               │
└────────────────────────────┬────────────────────────────┘
                             │ Goal Prompt
                             ▼
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator Agent                    │
│             (Task Breakdown & Delegation)               │
└──────┬──────────────────┬──────────────────┬────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Designer    │   │   Backend    │   │   Frontend   │
│   Agent      │   │   Engineer   │   │   Engineer   │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │   QA Tester    │
                 └───────┬────────┘
                         │
                         ▼
           ┌───────────────────────────┐
           │   SQLite Task Persistence │
           │   & Workspace ZIP Output  │
           └───────────────────────────┘