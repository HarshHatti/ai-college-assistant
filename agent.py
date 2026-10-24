import json
from datetime import date

import ollama

import tools
import study_planner
import document_search

MODEL = "llama3.2:latest"

TOOL_LOG = []  # the UI reads this to show tool results

# Map tool names (what the AI says) to real Python functions
TOOL_FUNCTIONS = {
    "add_task": tools.add_task,
    "list_tasks": tools.list_tasks,
    "complete_task": tools.complete_task,
    "create_study_plan": study_planner.generate_study_plan,
    "search_documents": document_search.search_documents,
}

# Descriptions the AI reads to decide which tool to use
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Create a new academic task (assignment, practical, study task) with a deadline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short task title"},
                    "deadline": {"type": "string", "description": "Deadline in YYYY-MM-DD format"},
                },
                "required": ["title", "deadline"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "Show the student's tasks, sorted by deadline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "done", "all"],
                        "description": "Which tasks to show. Default is pending.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task as done using its id number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "The id of the task"}
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_study_plan",
            "description": "Create a day-by-day study schedule for an exam.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Subject name"},
                    "exam_date": {"type": "string", "description": "Exam date in YYYY-MM-DD format"},
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of topics still to study",
                    },
                    "hours_per_day": {"type": "number", "description": "Study hours available per day"},
                },
                "required": ["subject", "exam_date", "topics", "hours_per_day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search the student's uploaded notes and PDFs. Use this for any question about their study material.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question or topic to look up"}
                },
                "required": ["question"],
            },
        },
    },
]


def get_system_prompt():
    today = date.today()
    return (
        "You are a helpful college assistant. Keep answers short and clear.\n"
        f"Today's date is {today.isoformat()} ({today.strftime('%A')}).\n"
        "Rules:\n"
        "- Use tools to create, list or complete tasks. Do not pretend.\n"
        "- Convert dates like '30 October' into YYYY-MM-DD using today's date.\n"
        "- If the student does not give a deadline, ask for it. Do not guess.\n"
        "- Only say a task was created or completed if the tool result says success is true.\n"
        "- If a tool returns an error, explain the error to the student.\n"
        "- To make a study plan, you need subject, exam date, topics and hours per day. Ask for anything missing. Use the create_study_plan tool and show the plan from its result.\n"
        "- For questions about the student's notes or study material, use search_documents first. Answer only from the results and mention the file name and page. If the results do not contain the answer, say so clearly, then give a general answer and label it 'From general knowledge, not your notes'.\n"
    )


def run_tool(name, args):
    """Run the requested tool safely and return its result dict."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return {"success": False, "error": f"Unknown tool: {name}"}
    try:
        return func(**args)
    except TypeError as e:
        return {"success": False, "error": f"Bad arguments: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Tool crashed: {e}"}


def looks_like_fake_tool_call(text):
    """The model sometimes types a tool call as text instead of really calling it."""
    t = (text or "").strip()
    return t.startswith("{") and ('"name"' in t or '"parameters"' in t)


def chat(messages):
    """Send messages to the AI. Run any tools it asks for. Return the final reply."""
    try:
        retried = False
        for _ in range(4):  # allow a few rounds of tool use
            response = ollama.chat(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                options={"temperature": 0},  # more predictable output
            )
            msg = response.message

            if not msg.tool_calls:
                if looks_like_fake_tool_call(msg.content) and not retried:
                    retried = True
                    messages.append({
                        "role": "user",
                        "content": "That was not a real tool call. If you need a tool, call it properly. "
                                   "If information is missing, ask me for it.",
                    })
                    continue
                if looks_like_fake_tool_call(msg.content):
                    return "Sorry, I could not process that. Please give all the details again."
                messages.append(msg)
                return msg.content

            messages.append(msg)
            for call in msg.tool_calls:
                name = call.function.name
                args = call.function.arguments
                result = run_tool(name, args)
                print(f"  [tool] {name}({args}) -> {result}")
                TOOL_LOG.append({"tool": name, "args": dict(args), "result": result})
                messages.append(
                    {"role": "tool", "tool_name": name, "content": json.dumps(result)}
                )
        return "Sorry, I could not complete that request."
    except ollama.ResponseError as e:
        return f"[Ollama error] {e.error}"
    except Exception as e:
        return f"[Could not reach Ollama] {e}. Is Ollama running?"


def main():
    print("Loading documents...")
    for pdf in document_search.DOCS_FOLDER.glob("*.pdf"):
        print(" ", document_search.index_pdf(pdf))

    messages = [{"role": "system", "content": get_system_prompt()}]
    print("College Assistant ready. Type 'quit' to exit.")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        print(f"Agent: {chat(messages)}")


if __name__ == "__main__":
    main()