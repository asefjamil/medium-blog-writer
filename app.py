import streamlit as st
import requests
import re
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

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
            st.success("✅ Gemini prompt generation succeeded.")
            return gemini_output
        else:
            st.warning("⚠️ Gemini response too short. Falling back to DeepSeek V3...")
    except Exception as e:
        st.warning(f"⚠️ Gemini failed. Falling back to DeepSeek V3...")

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
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers)
        if response.status_code == 200:
            st.success("✅ DeepSeek V3 fallback succeeded.")
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            st.error(f"❌ Fallback failed. Status code: {response.status_code}")
            return ""
    except Exception as e:
        st.error(f"❌ Prompt generation failed completely: {e}")
        return ""

def generate_blog_from_prompt(topic, prompt_text):
    headers_chutes = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    headers_fallback = {
        "Authorization": f"Bearer {OPENROUTER_V3_FREE_KEY}",
        "Content-Type": "application/json"
    }

    system_msg = f"You are a professional blog writer. Write a complete Medium-style, SEO-optimized blog on the topic: '{topic}'. Start the blog with a centered title. Each numbered section (e.g., 1. Introduction) must be followed by a well-developed paragraph. Use bullet points (-) only if clearly required as subpoints. Do not use markdown or symbols like **, ##, --, etc."

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
            st.warning("⚠️ Chutes failed. Trying fallback model...")
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers_fallback)
            if response.status_code == 200:
                st.success("✅ Blog generated using fallback model.")
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                st.error("❌ Blog generation failed completely.")
                return ""
    except Exception as e:
        st.error(f"❌ Blog generation error: {e}")
        return ""

def convert_blog_to_pdf(blog_text, topic):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    section_style = ParagraphStyle('section', parent=styles['Heading2'], fontSize=14, spaceAfter=10)
    body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=12, spaceAfter=8)
    title_style = ParagraphStyle('title', parent=styles['Title'], fontSize=18, alignment=1, spaceAfter=20)

    blog_elements = [Paragraph(topic.strip(), title_style)]

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

# --- STEP 3: UI ---
st.set_page_config(page_title="1-Click Blog Generator", layout="centered")
st.title("📝 1-Click Medium Blog Generator")

# Step 3a: Topic and Context Input
topic = st.text_input("Enter blog topic", key="topic_input")
context = st.text_area("Enter context (1–2 lines)", height=100)

# Step 3b: Generate Prompt
if st.button("Generate Prompt"):
    with st.spinner("🎨 Generating blog prompt..."):
        st.session_state.prompt = generate_prompt(topic, context)
    if st.session_state.prompt:
        st.success("✅ Prompt ready below.")
        st.text_area("Generated Prompt", value=st.session_state.prompt, height=200)

# Step 3c: Generate Blog
if "prompt" in st.session_state and st.session_state.prompt:
    if st.button("Generate Blog from Prompt"):
        with st.spinner("✍️ Generating blog content..."):
            blog = generate_blog_from_prompt(topic, st.session_state.prompt)
        if blog:
            st.success("✅ Blog generated below.")
            st.text_area("Blog Output", value=blog, height=300)

            # PDF download
            with st.spinner("📄 Creating PDF..."):
                pdf_file = convert_blog_to_pdf(blog, topic)
            st.download_button(label="📥 Download PDF", data=pdf_file, file_name=f"{topic.replace(' ', '_')}.pdf", mime="application/pdf")
