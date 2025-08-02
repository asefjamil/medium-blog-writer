import streamlit as st
import requests
import re
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

# --- STEP 1: CONFIGURATION ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
OPENROUTER_API_KEY = st.secrets["API_OR"]
OPENROUTER_V3_FREE_KEY = st.secrets["v3_free"]

# --- STEP 2: HELPER FUNCTIONS ---
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

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers_chutes)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers_fallback)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        st.error(f"Blog generation failed: {e}")
    return ""

def save_blog_to_pdf(blog_text, topic):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=60, bottomMargin=40)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Title'], fontSize=18, alignment=1, spaceAfter=20)
    section_style = ParagraphStyle('section', parent=styles['Heading2'], fontSize=14, spaceAfter=10)
    body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=12, spaceAfter=8)

    blog_elements = [Paragraph(topic.strip(), title_style)]
    for line in blog_text.split('
'):
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
    return buffer

# --- STEP 3: UI ---

st.title("📝 1-Click Medium Blog Generator")

# Step 3a: Topic and Context Input
if "prompt" not in st.session_state:
    st.session_state.prompt = ""
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "blog" not in st.session_state:
    st.session_state.blog = ""

with st.form("topic_form"):
    topic = st.text_input("Enter blog topic", value=st.session_state.topic)
    context = st.text_area("Enter short context", height=100)
    submitted = st.form_submit_button("Generate Prompt")

if submitted:
    prompt = generate_prompt(topic, context)
    st.session_state.prompt = prompt
    st.session_state.topic = topic
    st.success("Prompt generated successfully!")

# Step 3b: Show Prompt and Generate Blog
if st.session_state.prompt:
    st.subheader("🧠 Generated Prompt")
    st.code(st.session_state.prompt)

    if st.button("Generate Blog from Prompt"):
        blog = generate_blog(st.session_state.topic, st.session_state.prompt)
        if blog:
            st.session_state.blog = blog
            st.success("Blog generated successfully!")

# Step 3c: Show Blog and PDF Download
if st.session_state.blog:
    st.subheader("📄 Final Blog Output")
    st.text_area("Blog Preview", value=st.session_state.blog, height=400)

    pdf_buffer = save_blog_to_pdf(st.session_state.blog, st.session_state.topic)
    st.download_button(label="📥 Download Blog as PDF",
                       data=pdf_buffer.getvalue(),
                       file_name=f"blog_for_{re.sub(r'[^a-zA-Z0-9]+', '_', st.session_state.topic.strip())}.pdf",
                       mime="application/pdf")