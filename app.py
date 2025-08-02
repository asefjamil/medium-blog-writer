import streamlit as st
import requests
import re
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

# --- CONFIGURATION ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
OPENROUTER_API_KEY = st.secrets["API_OR"]
OPENROUTER_V3_FREE_KEY = st.secrets["v3_free"]

# --- HELPER FUNCTIONS ---

def generate_prompt(topic, context, quality_threshold=20):
    user_prompt = f"Generate a creative and detailed blog prompt for the topic: '{topic}'. Context: {context}"

    try:
        from google import generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        response = gemini_model.generate_content(user_prompt)
        gemini_output = response.text.strip()
        if len(gemini_output) >= quality_threshold:
            st.success("✅ Gemini succeeded.")
            return gemini_output
    except Exception as e:
        st.warning(f"⚠️ Gemini failed. Falling back to DeepSeek V3...")

    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_V3_FREE_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek/deepseek-chat-v3-0324",
            "messages": [
                {"role": "system", "content": "You are a creative prompt generator for blogs."},
                {"role": "user", "content": user_prompt}
            ]
        }
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            st.success("✅ DeepSeek V3 fallback succeeded.")
            return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        st.error("❌ Prompt generation failed.")
        return ""

def generate_blog_from_prompt(topic, prompt_text):
    st.info("🧠 Generating blog using Chutes (DeepSeek V3)...")
    system_msg = f"You are a professional blog writer. Write a complete Medium-style, SEO-optimized blog on the topic: '{topic}'. Start with a centered title. Each numbered section (e.g., 1. Introduction) must be followed by a detailed paragraph. Use bullet points (-) only for subpoints. No markdown or ## or symbols like **."

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
    if response.status_code == 200:
        st.success("✅ Blog generated using Chutes.")
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        st.warning("⚠️ Chutes failed. Trying DeepSeek fallback...")
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers_fallback)
        if response.status_code == 200:
            st.success("✅ Fallback blog generated.")
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            st.error("❌ Blog generation failed.")
            return ""

def save_blog_to_pdf(blog_text, topic):
    filename = f"blog_for_{re.sub(r'[^a-zA-Z0-9]+', '_', topic.strip())}.pdf"
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    blog_elements = []

    title_style = ParagraphStyle('title', parent=styles['Title'], fontSize=18, alignment=1, spaceAfter=20)
    section_style = ParagraphStyle('section', parent=styles['Heading2'], fontSize=14, spaceAfter=10)
    body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=12, spaceAfter=8)

    blog_elements.append(Paragraph(topic.strip(), title_style))

    for line in blog_text.split('\n'):
        clean_line = re.sub(r'[\*_#`>]+', '', line).strip()
        if not clean_line:
            blog_elements.append(Spacer(1, 0.2 * inch))
        elif re.match(r'^\d+\.\s', clean_line):
            blog_elements.append(Paragraph(clean_line, section_style))
        elif re.match(r'^-\s', clean_line):
            blog_elements.append(Paragraph(clean_line, body_style))
        else:
            blog_elements.append(Paragraph(clean_line, body_style))

    doc.build(blog_elements)
    buffer.seek(0)
    return buffer

# --- UI ---

st.title("📝 1-Click Medium Blog Generator")

if "prompt" not in st.session_state:
    st.session_state.prompt = ""

topic = st.text_input("Enter blog topic")
context = st.text_area("Enter context (1–2 lines)")

if st.button("Generate Prompt"):
    st.session_state.prompt = generate_prompt(topic, context)
    st.text_area("Generated Prompt", value=st.session_state.prompt, height=200)

if st.session_state.prompt:
    if st.button("Generate Blog from Prompt"):
        blog = generate_blog_from_prompt(topic, st.session_state.prompt)
        st.text_area("Blog Output", value=blog, height=300)
        if blog:
            pdf = save_blog_to_pdf(blog, topic)
            st.download_button("📥 Download PDF", data=pdf, file_name=f"{topic}.pdf", mime="application/pdf")
