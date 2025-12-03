"""
JEE Question Paper Generator - Streamlit Web UI
"""

import streamlit as st
import subprocess
import sys
import os
from pathlib import Path
import base64

# Page configuration
st.set_page_config(
    page_title="JEE Paper Generator",
    page_icon="📝",
    layout="wide"
)

# Initialize session state FIRST before any widgets
if 'generated_pdf' not in st.session_state:
    st.session_state.generated_pdf = None
if 'pdf_path' not in st.session_state:
    st.session_state.pdf_path = None

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #e7f3ff;
        border: 1px solid #b6d4fe;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">📝 JEE Question Paper Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Generate custom JEE Main practice papers with AI-powered question transformation</div>', unsafe_allow_html=True)

# Sidebar for options
st.sidebar.header("⚙️ Paper Configuration")

# Difficulty selection
difficulty = st.sidebar.selectbox(
    "Difficulty Level",
    options=["easy", "medium", "hard"],
    index=1,  # Default to medium
    help="Select the overall difficulty of the paper"
)

# Transform option
use_transform = st.sidebar.checkbox(
    "🤖 AI Transformation",
    value=False,
    help="Use LLM to rephrase questions (makes papers unique but takes longer)"
)

# Solutions option
include_solutions = st.sidebar.checkbox(
    "📋 Include Answer Key",
    value=True,
    help="Include answer key at the end of the paper"
)

# Paper info
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Paper Format")
st.sidebar.markdown("""
- **Physics**: 20 MCQ + 10 Integer
- **Chemistry**: 20 MCQ + 10 Integer  
- **Mathematics**: 20 MCQ + 10 Integer
- **Total**: 90 Questions
""")

# Main content area
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🎯 Selected Options")
    st.markdown(f"""
    - **Difficulty**: {difficulty.capitalize()}
    - **AI Transform**: {'Yes' if use_transform else 'No'}
    - **Answer Key**: {'Yes' if include_solutions else 'No'}
    """)
    
    # Generate button
    generate_btn = st.button("🚀 Generate Paper", type="primary", use_container_width=True)

with col2:
    st.markdown("### 📄 Generated Paper")
    
    # Placeholder for PDF display
    pdf_placeholder = st.empty()


def generate_paper(difficulty: str, transform: bool, solutions: bool, status_placeholder) -> tuple:
    """
    Generate paper by calling generate_paper.py
    Returns: (success, pdf_path, message)
    """
    # Build command - use sys.executable to ensure we use the same Python interpreter
    cmd = [sys.executable, "-u", "generate_paper.py", "--difficulty", difficulty]  # -u for unbuffered output
    
    if transform:
        cmd.append("--transform")
    
    if not solutions:
        cmd.append("--no-solutions")
    
    try:
        # Run the generator with real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=os.environ.copy(),
            bufsize=1  # Line buffered
        )
        
        output_lines = []
        pdf_path = None
        
        # Read output line by line
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            output_lines.append(line.rstrip())
            
            # Update status display (show last 15 lines)
            display_text = '\n'.join(output_lines[-15:])
            status_placeholder.code(display_text, language="text")
            
            # Check for PDF path
            if 'Output:' in line and '.pdf' in line:
                pdf_path = line.split('Output:')[-1].strip()
        
        process.wait(timeout=600)
        
        full_output = '\n'.join(output_lines)
        
        if process.returncode != 0:
            return False, "", f"Generation failed (exit code {process.returncode}):\n{full_output[-2000:]}"
        
        # Check if we found the PDF path
        if pdf_path and os.path.exists(pdf_path):
            return True, pdf_path, "Paper generated successfully!"
        
        # Try to find the most recent PDF in generated_papers
        papers_dir = Path("generated_papers")
        if papers_dir.exists():
            pdfs = sorted(papers_dir.glob("*.pdf"), key=os.path.getmtime, reverse=True)
            if pdfs:
                return True, str(pdfs[0]), "Paper generated successfully!"
        
        return False, "", f"Generation completed but no PDF found:\n{full_output[-2000:]}"
        
    except subprocess.TimeoutExpired:
        process.kill()
        return False, "", f"Generation timed out (>5 minutes)\nLast output:\n{chr(10).join(output_lines[-20:])}"
    except Exception as e:
        return False, "", f"Error: {str(e)}"


def display_pdf(pdf_path: str):
    """Display PDF in the Streamlit app"""
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Encode PDF to base64
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Create PDF display using iframe
        pdf_display = f'''
        <iframe 
            src="data:application/pdf;base64,{base64_pdf}" 
            width="100%" 
            height="800px" 
            type="application/pdf"
            style="border: 1px solid #ccc; border-radius: 5px;">
        </iframe>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        return True
    except Exception as e:
        st.error(f"Error displaying PDF: {e}")
        return False


# Handle generation
if generate_btn:
    status_container = st.empty()
    with status_container.container():
        st.markdown("#### 🔄 Generating paper...")
        status_output = st.empty()
        status_output.code("Starting generation...", language="text")
        
    success, pdf_path, message = generate_paper(difficulty, use_transform, include_solutions, status_output)
    
    status_container.empty()  # Clear the status
    
    if success:
        st.session_state.generated_pdf = pdf_path
        st.session_state.pdf_path = pdf_path
        st.success(f"✅ {message}")
    else:
        st.error(f"❌ {message}")

# Display PDF if available
if st.session_state.generated_pdf:
    pdf_path = st.session_state.generated_pdf
    
    with col2:
        # Download button
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name=os.path.basename(pdf_path),
            mime="application/pdf",
            use_container_width=True
        )
        
        # Display PDF
        display_pdf(pdf_path)
        
        # Also show LaTeX source option
        tex_path = pdf_path.replace('.pdf', '.tex')
        if os.path.exists(tex_path):
            with st.expander("📜 View LaTeX Source"):
                with open(tex_path, 'r', encoding='utf-8') as f:
                    st.code(f.read(), language='latex')

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ About")
st.sidebar.markdown("""
This tool generates JEE Main practice papers from a curated dataset of 1300+ questions.

**Features:**
- Multiple difficulty levels
- AI-powered question rephrasing
- Professional PDF output
- Answer key included
""")

# Instructions if no PDF yet
if not st.session_state.generated_pdf:
    with col2:
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown("""
        ### 👋 Welcome!
        
        1. Select your preferred difficulty level from the sidebar
        2. Enable AI transformation for unique questions (optional)
        3. Click **Generate Paper** to create your practice paper
        4. Download or view the PDF directly in the browser
        
        **Note:** AI transformation takes longer but creates unique question variations.
        """)
        st.markdown('</div>', unsafe_allow_html=True)
