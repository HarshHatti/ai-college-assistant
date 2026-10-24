# AI College Assistant

A local AI agent for students: PDF Q&A, study planner and task manager.

## Features
- Ask questions about uploaded PDF notes
- Generate a day-by-day study plan
- Create and view tasks with deadlines
- Real tool calling with Python and Ollama

## Requirements
- Python 3.10+
- Ollama: https://ollama.com
- Models: `ollama pull llama3.2` and `ollama pull embeddinggemma`

## Run
pip install -r requirements.txt
python -m streamlit run app.py
