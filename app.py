from flask import Flask, request, jsonify, render_template, send_from_directory
from PyPDF2 import PdfReader
import pdfplumber
from fpdf import FPDF
from io import BytesIO
import base64
import time
import re
import os
import torch
import arabic_reshaper
from bidi.algorithm import get_display
from transformers import BartForConditionalGeneration, BartTokenizer
import nltk
nltk.download('punkt')

import google.generativeai as genai

# Configure Google Gemini API
genai.configure(api_key="AIzaSyCLkvelAIwv7iDVP99QUdw2JVdIyVP7b1w")  # Replace with your actual API key
model1 = genai.GenerativeModel("gemini-1.5-flash")

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Load BART model and tokenizer (adjust paths accordingly)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

tokenizer = BartTokenizer.from_pretrained(r"model\bart-summarizer-cnn")
model = BartForConditionalGeneration.from_pretrained(r"model\bart-summarizer-cnn1").to(device)
model.eval()

import unicodedata

def clean_text(text):
    # Normalize unicode characters (NFKD)
    text = unicodedata.normalize('NFKD', text)
    # Remove surrogate characters that cause encoding errors
    text = re.sub(r'[\ud800-\udfff]', '', text)
    # Optionally remove non-ASCII chars
    text = ''.join(c for c in text if ord(c) < 128)
    # Attempt to encode/decode safely with UTF-16
    try:
        text = text.encode('utf-16', 'replace').decode('utf-16', 'replace')
    except Exception:
        pass
    return text

def extract_text_from_pdf(file):
    text = ""
    try:
        pdf = PdfReader(file)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += clean_text(page_text) + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"PyPDF2 extraction failed: {e}")

    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += clean_text(page_text) + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfplumber extraction failed: {e}")

    return None

# Create pdf functrion
def split_long_words(text, max_len=50):
    words = text.split()
    new_words = []
    for w in words:
        if len(w) > max_len:
            chunks = [w[i:i+max_len] for i in range(0, len(w), max_len)]
            new_words.append('\u200b'.join(chunks))  # zero-width space
        else:
            new_words.append(w)
    return ' '.join(new_words)

# _________________________________
def reshape_text(text):
    # Reshape and reorder for Indic scripts to display correctly
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def is_devanagari(text):
    return any('\u0900' <= c <= '\u097F' for c in text)

def is_bold_line(text):
    return text.strip().startswith(("Hindi:", "Marathi:", "English:", "Summary"))

def create_multilang_pdf(text):


    language = request.form.get("language", "english").strip().lower()

    if language in ['hindi', 'marathi']:
        text = split_long_words(text)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(15)
        pdf.set_right_margin(15)

        # Add fonts
        pdf.add_font('NotoSans', '', 'fonts/NotoSans-Regular.ttf', uni=True)
        pdf.add_font('NotoSans', 'B', 'fonts/NotoSans-Bold.ttf', uni=True)

        pdf.add_font('NotoSansDevanagari', '', 'fonts/NotoSansDevanagari-Regular.ttf', uni=True)
        pdf.add_font('NotoSansDevanagari', 'B', 'fonts/NotoSansDevanagari-Bold.ttf', uni=True)

        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln()
                continue

            if is_devanagari(line):
                # reshape & reorder text
                line = reshape_text(line)
                pdf.set_font('NotoSansDevanagari', '', 12)
            else:
                pdf.set_font('NotoSans', '', 12)

            pdf.multi_cell(0, 10, line)

        pdf_bytes = BytesIO()
        pdf.output(pdf_bytes, 'F')
        pdf_bytes.seek(0)
        return pdf_bytes.getvalue()
    # ------------------------------------------
    
    else:
        text = clean_text(text)  # Add this line to clean the summary

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)

        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln()
                continue

            parts = re.split(r'(\\.?\\*)', line)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    text_part = part[2:-2]
                    pdf.set_font("Arial", 'B', 12)

                elif part.startswith('* **') and part.endswith('**'):
                    text_part = part[2:-2]
                    pdf.set_font("Arial", 'B', 12)

                else:
                    text_part = part
                    pdf.set_font("Arial", '', 12)
                pdf.write(5, text_part)
            pdf.ln(10)

        pdf_bytes = BytesIO()
        pdf.output(pdf_bytes, 'F')
        pdf_bytes.seek(0)
        return pdf_bytes.getvalue()


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        start_time = time.time()

        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400

        file = request.files['file']
        if file.filename == '' or not file.filename.lower().endswith('.pdf'):
            return jsonify({"success": False, "error": "Invalid PDF file"}), 400

        # Extract text from PDF
        text = extract_text_from_pdf(file)
        if not text:
            return jsonify({"success": False, "error": "No readable text found in PDF"}), 400

        summary_type = request.form.get("summary_type", "abstractive").lower()

        if summary_type == "abstractive":
            from math import ceil

            def chunk_text(text, chunk_size=1024):
                tokens = tokenizer.tokenize(text)
                num_chunks = ceil(len(tokens) / chunk_size)
                chunks = []
                for i in range(num_chunks):
                    chunk_tokens = tokens[i * chunk_size : (i + 1) * chunk_size]
                    chunk_text = tokenizer.convert_tokens_to_string(chunk_tokens)
                    chunks.append(chunk_text)
                return chunks

            chunks = chunk_text(text, chunk_size=1024)
            summaries = []

            for chunk in chunks:
                length_percent = int(request.form.get("summary_length", 100))
                max_possible_tokens = 1024
                max_length = int((length_percent / 100.0) * max_possible_tokens)
                max_length = max(40, min(max_length, 1024))
                min_length = int(max_length * 0.8) if max_length >= 50 else max_length - 5
                min_length = max(20, min_length)

                inputs = tokenizer(chunk, return_tensors="pt", max_length=1024, truncation=True).to(device)

                summary_ids = model.generate(
                    inputs["input_ids"],
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=True,
                    top_k=50,
                    top_p=0.9,
                    temperature=1.2,
                    repetition_penalty=2.0
                )

                chunk_summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
                summaries.append(chunk_summary)

            final_summary = "\n\n".join(summaries)

        elif summary_type == "extractive":
            import heapq
            from nltk.tokenize import sent_tokenize

            length_percent = int(request.form.get("summary_length", 30))
            sentences = sent_tokenize(text)
            num_sentences = max(1, int(len(sentences) * (length_percent / 100.0)))

            sentence_scores = {sent: len(sent) for sent in sentences}
            best_sentences = heapq.nlargest(num_sentences, sentence_scores, key=sentence_scores.get)

            best_sentences_sorted = sorted(best_sentences, key=lambda s: sentences.index(s))

            final_summary = "\n".join(best_sentences_sorted)
        else:
            return jsonify({"success": False, "error": "Invalid summary type"}), 400

        # Language handling
        selected_lang = request.form.get("language", "english").strip().lower() or "english"

        if selected_lang == "english":
            final_summary = clean_text(final_summary)
            instruction = (
                f"{final_summary}\n\n"
                "keep the lenght of content as it is. "
                "Do not add, remove, or summarize any information. "
                "Just organize into proper structure. "
                "Bold main points. "
                "Make the structure, format, and line breaks suitable for the given text."
            )
            response = model1.generate_content(instruction)
            final_summary = response.text.strip()
        else:
            instruction = (
                f"Translate the following structured summary into {selected_lang}:\n\n"
                f"{final_summary}\n\n"
                "keep the lenght of content as it is. "
                "Do not add, remove, or summarize any information. "
                "Keep the content exactly the same but translated word-by-word into the target language. "
                "Bold main points and organize well. "
                "Make the structure, format, and line breaks suitable for the given text. "
                "Again remember keep the lenght of content as it is."
            )
            response = model1.generate_content(instruction)
            final_summary = response.text.strip()

        pdf_bytes = create_multilang_pdf(final_summary)

        return jsonify({
            "success": True,
            "summary": final_summary,
            "pdf_bytes": base64.b64encode(pdf_bytes).decode('utf-8'),
            "processing_time": f"{time.time() - start_time:.2f}s"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Processing failed: {str(e)}"
        }), 500


if __name__ == "__main__":
    # Use debug=False in production
    app.run(host='0.0.0.0', port=5000, debug=True)
