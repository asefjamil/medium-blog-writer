# ✅ 1-Click Medium Blog Generator (Streamlit version)

import streamlit as st
import re
import requests
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from google import generativeai as genai

# ✅ Load API Keys from secrets
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]

# ✅ Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="1-Click Medium Blog", layout="centered")
st.title("📝 1-Click Medium Blog Generator")

# ✅ Inputs
with st.form("blog_form"):
    topic = st.text_input("Enter your blog topic")
    context = st.text_area("Optional context or angle for the blog")
    submitted = st.form_submit_button("Generate Blog")

if submitted and topic.strip():
    user_prompt = f"Generate a creative and detailed blog prompt for the topic: '{topic}'. Context: {context}"

    # STEP 1: Generate Blog Prompt using Gemini → fallback: Atlas
    try:
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        prompt_response = gemini_model.generate_content(user_prompt)
        prompt_text = prompt_response.text.strip()
        if len(prompt_text) < 30:
            raise ValueError("Prompt too short")
        st.success("✅ Prompt generated using Gemini")
    except:
        st.warning("⚠️ Gemini failed, using DeepSeek Atlas as fallback")
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek/deepseek-chat-v3-0324",
            "messages": [
                {"role": "system", "content": "You are a creative prompt generator for blogs."},
                {"role": "user", "content": user_prompt}
            ]
        }
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers)
        prompt_text = response.json()['choices'][0]['message']['content'].strip()
        st.success("✅ Prompt generated using DeepSeek Atlas")

    st.markdown("---")
    st.markdown("**🧠 Finalized Prompt:**")
    st.code(prompt_text)

    # STEP 2: Generate Blog using Gemini → fallback: Chutes
    system_msg = f"""You are a professional blog writer. Write a detailed, structured, and SEO-optimized blog on the topic: '{topic}'.
- Begin with a centered blog title (just the title).
- Use numbered section headers (e.g., 1. Introduction).
- Under each section, write one or more detailed paragraphs.
- Use bullet points (-) only if the section clearly needs a list.
- Do NOT use markdown (e.g., ###, **, ##, --).
- Ensure the writing is clean, human-readable, and print-friendly."""

    try:
        blog_response = gemini_model.generate_content(f"{system_msg}\n\nPrompt:\n{prompt_text}")
        blog_text = blog_response.text.strip()
        if len(blog_text) < 100:
            raise ValueError("Blog too short")
        st.success("✅ Blog generated using Gemini")
    except:
        st.warning("⚠️ Gemini failed, using DeepSeek Chutes as fallback")
        data = {
            "model": "deepseek/deepseek-chat-v3-0324",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt_text}
            ]
        }
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers)
        blog_text = response.json()['choices'][0]['message']['content'].strip()
        st.success("✅ Blog generated using DeepSeek Chutes")

    # STEP 3: Generate PDF in memory
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
        if not clean_line or re.match(r'^-+$', clean_line):
            blog_elements.append(Spacer(1, 0.2 * inch))
            continue
        if re.match(r'^\d+\.\s', clean_line):
            blog_elements.append(Paragraph(clean_line, section_style))
        elif re.match(r'^-\s', clean_line):
            blog_elements.append(Paragraph(clean_line, body_style))
        else:
            blog_elements.append(Paragraph(clean_line, body_style))

    doc.build(blog_elements)
    buffer.seek(0)

    st.markdown("---")
    st.download_button(
        label="📥 Download Your Blog as PDF",
        data=buffer,
        file_name=f"blog_for_{re.sub(r'[^a-zA-Z0-9]+', '_', topic.lower())}.pdf",
        mime="application/pdf"
    )
