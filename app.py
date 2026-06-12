import gradio as gr
import requests

def ask_question(question):
    response = requests.get(
        "https://upamnyu12-lex.hf.space/query",
        params={"q": question}
    )
    if response.status_code == 200:
        return response.json().get("answer", "No answer")
    return "Error contacting API"

gr.ChatInterface(fn=ask_question).launch()