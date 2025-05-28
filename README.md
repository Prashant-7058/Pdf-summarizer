

# 📝 Multilingual PDF Summarizer (English | हिंदी | मराठी)

This project is a **Flask-based web tool** that allows users to **upload PDF files**, generate **custom summaries**, and download the results in **multiple languages** — including **English**, **Hindi**, and **Marathi**.

It supports **accurate rendering of Indic scripts** using proper font embedding and text reshaping to ensure correct display in the output PDF.


## ✨ Features

- Supports English, Hindi (हिंदी), and Marathi (मराठी)
- Creates downloadable PDF summaries with proper formatting


## 🔧 Technologies Used

* Python 🐍
* Flask 🌐
* FPDF (for PDF generation)
* Custom fonts: NotoSans

## Setup Instructions
- Create virtual environment: 
  python -m venv venv

- Activate the environment : 
  venv\Scripts\activate   # For Windows
  OR
  source venv/bin/activate   # For macOS/Linux

- Install dependencies:
  pip install -r requirements.txt

- Replace your API key

  Open app.py and replace the placeholder with your actual API key where required. (gemini api key)

- run :
  python app.py


