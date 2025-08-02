# ✅ Final Streamlit App: Prompt Generator with Fallback

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
        from google import generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        response = gemini_model.generate_content(user_prompt)
        output = response.text.strip()
        if len(output) >= 30:
            st.success("✅ Prompt generated using Gemini.")
            return output
        else:
            st.warning("⚠️ Gemini too short. Falling back to DeepSeek V3...")
    except:
        st.warning("⚠️ Gemini failed. Falling back to DeepSeek V3...")

    try:
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
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers)
        if response.status_code == 200:
            st.success("✅ Prompt generated using fallback DeepSeek V3.")
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            st.error(f"❌ Fallback failed. Status code: {response.status_code}")
            return ""
    except:
        st.error("❌ Prompt generation failed.")
        return ""

def generate_blog_from_prompt(topic, prompt_text):
    system_msg = f"You are a professional blog writer. Write a complete Medium-style, SEO-optimized blog on the topic: '{topic}'. Start the blog with a centered title. Each numbered section (e.g., 1. Introduction) must be followed by a well-developed paragraph. Use bullet points (-) only if clearly required as subpoints. Do not use markdown or symbols like **, ##, --, etc."

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

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers_chutes)
        if response.status_code == 200:
            st.success("✅ Blog generated using DeepSeek V3 (Chutes).")
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            st.warning("⚠️ Chutes failed. Trying fallback...")
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers_fallback)
            if response.status_code == 200:
                st.success("✅ Blog generated using fallback DeepSeek V3.")
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                st.error(f"❌ Fallback failed. Status code: {response.status_code}")
                return ""
    except:
        st.error("❌ Blog generation failed.")
        return ""

def save_blog_to_pdf(blog_text, topic):
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
            continue
        if re.match(r'^\d+\.\s', clean_line):
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

topic = st.text_input("Enter blog topic")
context = st.text_area("Enter context (1–2 lines)", height=80)

if st.button("Generate Prompt"):
    with st.spinner("⏳ Generating..."):
        prompt = generate_prompt(topic, context)
        st.session_state["prompt"] = prompt

if "prompt" in st.session_state:
    st.subheader("Generated Prompt")
    st.write(st.session_state["prompt"])
    if st.button("Generate Blog from Prompt"):
        with st.spinner("⏳ Writing blog..."):
            blog = generate_blog_from_prompt(topic, st.session_state["prompt"])
            st.session_state["blog"] = blog

if "blog" in st.session_state:
    st.subheader("Generated Blog")
    st.write(st.session_state["blog"])
    pdf_buffer = save_blog_to_pdf(st.session_state["blog"], topic)
    st.download_button("📄 Download Blog as PDF", data=pdf_buffer, file_name=f"{topic}.pdf", mime="application/pdf")
