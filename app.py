import streamlit as st
import requests
import re
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

# --- CONFIGURATION ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
OPENROUTER_API_KEY = st.secrets["API_OR"]
OPENROUTER_V3_FREE_KEY = st.secrets["v3_free"]

# --- HELPER FUNCTIONS ---
def generate_prompt(topic, context):
    user_prompt = f"Generate a creative and detailed blog prompt for the topic: '{topic}'. Context: {context}"
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_V3_FREE_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-chat-v3-0324",
                "messages": [
                    {"role": "system", "content": "You are a creative blog prompt generator."},
                    {"role": "user", "content": user_prompt}
                ]
            }
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        st.error(f"Prompt generation failed: {e}")
    return ""

def generate_blog(topic, prompt_text):
    system_msg = f'''You are a professional blog writer. Write a detailed, structured, and SEO-optimized blog on the topic: '{topic}'.
Begin with a centered blog title.
Use numbered section headers (e.g., 1. Introduction).
Under each section, write one or more detailed paragraphs.
Use bullet points (-) only when clearly needed.
Avoid markdown (##, **, --) and ensure clear formatting.'''

    headers_chutes = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    headers_fallback = {
        "Authorization": f"Bearer {OPENROUTER_V3_FREE_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek/deepseek-chat-v3-0324",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt_text}
        ]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers_chutes)
    if response.status_code != 200:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers_fallback)

    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        st.error(f"Blog generation failed with status {response.status_code}")
        return ""

def create_pdf(blog_text, topic):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Title'], fontSize=18, alignment=1, spaceAfter=20)
    section_style = ParagraphStyle('section', parent=styles['Heading2'], fontSize=14, spaceAfter=10)
    body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=12, spaceAfter=8)

    elements = [Paragraph(topic, title_style)]
    for line in blog_text.split('\n'):
        clean_line = re.sub(r'[\*_#`>]+', '', line).strip()
        if not clean_line or re.match(r'^-+$', clean_line):
            elements.append(Spacer(1, 0.2 * inch))
        elif re.match(r'^\d+\.\s', clean_line):
            elements.append(Paragraph(clean_line, section_style))
        elif re.match(r'^-\s', clean_line):
            elements.append(Paragraph(clean_line, body_style))
        else:
            elements.append(Paragraph(clean_line, body_style))
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- UI ---
st.title("🧠 1-Click Medium Blog Generator")

topic = st.text_input("Enter Blog Topic")
context = st.text_area("Enter Blog Context (1–2 lines)")

if st.button("Generate Prompt"):
    prompt = generate_prompt(topic, context)
    if prompt:
        st.subheader("Generated Prompt")
        st.text_area("Prompt", prompt, height=200)

        if st.button("Generate Blog from Prompt"):
            blog = generate_blog(topic, prompt)
            if blog:
                st.subheader("Generated Blog")
                st.text_area("Blog", blog, height=400)
                pdf = create_pdf(blog, topic)
                st.download_button("📄 Download Blog as PDF", data=pdf, file_name=f"blog_for_{topic}.pdf", mime="application/pdf")