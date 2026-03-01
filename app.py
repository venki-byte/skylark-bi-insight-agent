"""
app.py — Skylark BI Agent
=========================
Tries Gemini first. Falls back to Groq on quota/rate-limit errors.
Tool loop is guarded (max 6 rounds) to prevent infinite retries.
"""

import os
import json
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
import groq

from monday_tools import dispatch_tool, TOOL_DEFINITIONS
from skylark_schema import SYSTEM_PROMPT

load_dotenv()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Skylark BI Agent", page_icon="🚀", layout="centered")
st.title("🚀 Skylark BI Agent")
st.caption("Ask anything about your deals or work orders.")

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ─────────────────────────────────────────────
# LLM CLIENTS
# ─────────────────────────────────────────────
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client   = groq.Client(api_key=os.getenv("GROQ_API_KEY"))

# ─────────────────────────────────────────────
# TOOL SCHEMAS
# Gemini and Groq need different formats.
# IMPORTANT: No "enum" in Groq schema — Llama rejects it with a 400.
# ─────────────────────────────────────────────

GEMINI_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=t["parameters"],
        )
    ])
    for t in TOOL_DEFINITIONS
]

# Groq: strip "enum" from every property — Llama 3.3 rejects schemas containing it
def _groq_safe_properties(props: dict) -> dict:
    return {
        k: {pk: pv for pk, pv in v.items() if pk != "enum"}
        for k, v in props.items()
    }

GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": {
                "type": "object",
                "properties": _groq_safe_properties(t["parameters"]["properties"]),
                "required": t["parameters"].get("required", []),
            },
        },
    }
    for t in TOOL_DEFINITIONS
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _is_quota_error(e: Exception) -> bool:
    msg = str(e).lower()
    return "429" in msg or "resource_exhausted" in msg or "quota" in msg or "rate limit" in msg


def _run_tool(name: str, args: dict, status) -> dict:
    """Execute a tool and return result dict. Logs to the status widget."""
    status.write(f"🛠️ **{name}** — `{json.dumps(args)}`")
    return dispatch_tool(name, args)


# ─────────────────────────────────────────────
# GEMINI CALL
# ─────────────────────────────────────────────

MAX_TOOL_ROUNDS = 6

def call_gemini(user_input: str, history: list[dict], status) -> str:
    # Build contents: past turns + new user message
    contents: list = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=GEMINI_TOOLS,
    )

    for _ in range(MAX_TOOL_ROUNDS):
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        fn_part = next((p for p in candidate.content.parts if p.function_call), None)

        if fn_part is None:
            return response.text  # Final answer — no more tool calls

        fn = fn_part.function_call
        args = {k: v for k, v in fn.args.items()}
        tool_result = _run_tool(fn.name, args, status)

        # Append model turn + tool result to conversation
        contents.append(candidate.content)
        contents.append(types.Content(
            role="tool",
            parts=[types.Part(
                function_response=types.FunctionResponse(
                    name=fn.name,
                    response={"result": json.dumps(tool_result, default=str)},
                )
            )],
        ))

    return response.text  # Return whatever exists after hitting round limit


# ─────────────────────────────────────────────
# GROQ CALL
# ─────────────────────────────────────────────

def call_groq(user_input: str, history: list[dict], status) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Include past conversation turns
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_input})

    for _ in range(MAX_TOOL_ROUNDS):
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=GROQ_TOOLS,
            tool_choice="auto",
            temperature=0.0,
            max_tokens=4096,
        )

        msg_out = response.choices[0].message
        tool_calls = msg_out.tool_calls

        if not tool_calls:
            return msg_out.content or ""  # Final answer

        # Append assistant message with tool_calls in the exact format Groq expects
        messages.append({
            "role": "assistant",
            "content": msg_out.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,  # raw JSON string
                    },
                }
                for tc in tool_calls
            ],
        })

        # Execute all tool calls and append results
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                args = {}

            tool_result = _run_tool(tc.function.name, args, status)
            tool_result_str = json.dumps(tool_result, default=str)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": tool_result_str,
            })

    # Exhausted rounds — force a plain text answer from accumulated results
    messages.append({
        "role": "user",
        "content": "Please summarise the tool results above and give a final answer now.",
    })
    final = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=2048,
    )
    return final.choices[0].message.content or ""


# ─────────────────────────────────────────────
# MAIN RESPONSE ORCHESTRATOR
# ─────────────────────────────────────────────

def get_ai_response(user_input: str) -> str | None:
    # History excludes the current user message (not yet appended)
    history = st.session_state.messages

    with st.status("📡 Querying data...", expanded=True) as status:

        # ── Try Gemini ──────────────────────────────
        try:
            answer = call_gemini(user_input, history, status)
            status.update(label="✅ Done (Gemini)", state="complete", expanded=False)
            return answer

        except Exception as gemini_err:
            if not _is_quota_error(gemini_err):
                # Real error, not quota — surface it directly
                status.update(label="❌ Gemini error", state="error")
                st.error(f"Gemini error: {gemini_err}")
                return None

            # ── Quota hit → fall back to Groq ──────
            status.write("⚠️ Gemini quota hit — switching to Groq (Llama 3.3 70B)...")

            try:
                answer = call_groq(user_input, history, status)
                status.update(label="✅ Done (Groq fallback)", state="complete", expanded=False)
                return answer

            except Exception as groq_err:
                status.update(label="❌ Both providers failed", state="error")
                st.error(f"Groq also failed: {groq_err}")
                return None


# ─────────────────────────────────────────────
# CHAT INTERFACE
# ─────────────────────────────────────────────

if prompt := st.chat_input("Ask about your deals or work orders..."):

    # Store + display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get + display AI response
    with st.chat_message("assistant"):
        answer = get_ai_response(prompt)
        if answer:
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})