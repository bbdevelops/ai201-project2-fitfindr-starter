"""
app.py

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
from utils.style_profile import load_profile, save_profile, format_profile_summary


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Returns a 4-tuple: (listing_text, outfit_suggestion, fit_card, profile_summary)
    """
    if not user_query or not user_query.strip():
        return "Please enter a search query.", "", "", format_profile_summary(load_profile())

    wardrobe = get_example_wardrobe() if wardrobe_choice == "Example wardrobe" else get_empty_wardrobe()
    session = run_agent(user_query, wardrobe)

    if session["error"]:
        return session["error"], "", "", format_profile_summary(load_profile())

    item = session["selected_item"]

    pc = session.get("price_comparison") or {}
    price_verdict = ""
    if pc.get("verdict") and pc["verdict"] != "unknown":
        price_verdict = f"\nPrice verdict: {pc['verdict']} — {pc.get('reasoning', '')}"

    trends = session.get("trends") or {}
    trend_line = ""
    if trends.get("trends"):
        trend_line = f"\nTrending styles: {', '.join(trends['trends'])}"

    retry_note = session.get("retry_note")
    retry_banner = f"ℹ️ No exact matches — retried with {retry_note}.\n\n" if retry_note else ""

    listing_text = retry_banner + (
        f"Title: {item.get('title', 'N/A')}\n"
        f"Price: ${item.get('price', 0):.2f}\n"
        f"Size: {item.get('size', 'N/A')}\n"
        f"Condition: {item.get('condition', 'N/A')}\n"
        f"Platform: {item.get('platform', 'N/A')}\n"
        f"Category: {item.get('category', 'N/A')}\n"
        f"Colors: {', '.join(item.get('colors', []))}\n"
        f"Brand: {item.get('brand') or 'Unlisted'}\n"
        f"Description: {item.get('description', '')}"
        f"{price_verdict}"
        f"{trend_line}"
    )

    profile_summary = format_profile_summary(session.get("style_profile") or load_profile())
    return listing_text, session["outfit_suggestion"], session["fit_card"], profile_summary


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        with gr.Row():
            submit_btn = gr.Button("Find it", variant="primary")
            clear_profile_btn = gr.Button("Clear Style Profile", variant="secondary")

        profile_display = gr.Textbox(
            label="🧠 Your Style Profile (remembered across sessions)",
            value=format_profile_summary(load_profile()),
            lines=1,
            interactive=False,
        )

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        def clear_profile():
            save_profile({})
            return format_profile_summary(load_profile())

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output, profile_display],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output, profile_display],
        )
        clear_profile_btn.click(
            fn=clear_profile,
            inputs=[],
            outputs=[profile_display],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
