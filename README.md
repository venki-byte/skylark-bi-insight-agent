# Skylark BI Agent – Monday.com AI Assistant

[![Streamlit App](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B)](https://your-app-url.streamlit.app)  
Ask natural language questions about your Monday.com sales deals and work orders. The agent understands your data schema, fetches live information via GraphQL, and returns clean, conversational answers.

## 🔧 Tech Stack
- **Frontend**: Streamlit
- **LLMs**: Google Gemini 2.0 Flash (primary), Groq Llama 3.3‑70B (fallback)
- **API**: Monday.com GraphQL API
- **Language**: Python 3.10+

## 📁 File Overview

### `skylark_schema.py`
- Defines the **board schemas** for *Deal Funnel* and *Work Order Tracker* – column names, actual Monday column IDs, data types, known categorical values, and join relationships.
- Builds the **system prompt** that is injected into every LLM call. The prompt tells the model:
  - Which tools are available and how to use them.
  - The correct column IDs to use in tool parameters.
  - Important relationships (e.g., `Deal Name` ↔ `Deal name masked`).
  - Empty columns that should never be queried.

### `monday_tools.py`
Contains all Monday.com integration logic:

- **Normalization pipeline** – cleans raw Monday values (strips `(Masked)`, currency symbols, converts dates, handles sentinels).
- **Three‑tier retrieval**:
  1. **Aggregation** – fetches only a single numeric column and sums/counts in Python (lightweight).
  2. **Targeted search** – uses Monday’s server‑side `query_params` to filter on categorical columns.
  3. **Full fetch** – cursor‑paginated retrieval of all rows (fallback).
- **Tool functions** – `get_deal_funnel`, `get_work_orders`, `get_unique_values` – callable by the LLM.
- **Dispatcher** – routes LLM tool calls to the correct Python function.

### `app.py`
Streamlit application that:

- Maintains **conversation history** in `session_state`.
- Orchestrates the LLM: first tries **Gemini**, falls back to **Groq** on quota errors.
- Handles the **tool‑calling loop** (up to 6 rounds) to satisfy complex queries.
- Displays the final answer and any intermediate tool calls.

## 🚀 Setup & Run

1. **Clone the repository**
   ```bash
   git clone https://github.com/venki-byte/skylark-bi-insight-agent.git
   cd skylark-bi-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables** (create a `.env` file)
   ```
   MONDAY_API_TOKEN=your_monday_token
   DEAL_FUNNEL_BOARD_ID=your_deal_funnel_board_id
   WORK_ORDER_BOARD_ID=your_work_order_board_id
   GEMINI_API_KEY=your_gemini_key
   GROQ_API_KEY=your_groq_key
   ```

4. **Run the app**
   ```bash
   streamlit run app.py
   ```

## 💬 Example Questions
- “What is the total amount for `alias_160` in the work order tracker?”
- “List all deals in the Mining sector with their masked deal value.”

## ✨ Key Features
- **Provider fallback** – automatically switches to Groq when Gemini quota is exhausted.
- **Data normalization** – ensures the LLM receives clean, typed values (floats, ISO dates, lowercase strings).
- **Efficient retrieval** – fetches only necessary data; never transfers whole boards unless required.
- **Conversation memory** – multi‑turn dialogues are supported via Streamlit session state.
- **Self‑validating schema** – included a checker script to verify column IDs match the actual Monday board.

## 📊 Live Demo
Try it yourself: [https://your-app-url.streamlit.app](https://your-app-url.streamlit.app)

---

Built for the Skylark Drones AI Engineer assignment – demonstrates production‑ready integration of LLMs with real‑world APIs.