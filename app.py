"""Gradio web UI for the Baltimore restaurant RAG pipeline.

Run: python app.py
Open: http://localhost:7860
"""

import gradio as gr

from generate import ask


def handle_query(question):
    if not question or not question.strip():
        return "", ""
    result = ask(question.strip())
    sources = "\n".join(f"• {s}" for s in result["sources"])
    return result["answer"], sources


with gr.Blocks(title="Baltimore Restaurant Guide") as demo:
    gr.Markdown("# The Unofficial Guide — Baltimore Restaurants")
    inp = gr.Textbox(
        label="Your question",
        placeholder="Where can I get crab cakes in Baltimore?",
    )
    btn = gr.Button("Ask")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)
    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

if __name__ == "__main__":
    demo.launch()
