import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS # We will use this in a new way
from dotenv import load_dotenv
import google.generativeai as genai
import fitz

load_dotenv()
app = Flask(__name__)

# --- THIS IS THE IMPORTANT CHANGE ---
# We are now being specific about who can talk to our server.
CORS(app, resources={r"/api/*": {"origins": "https://astounding-figolla-545b70.netlify.app"}})

try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Please check your .env file.")
    genai.configure(api_key=api_key)
    print("Gemini API configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

def extract_text_from_pdf(pdf_file):
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

@app.route('/api/generate', methods=['POST'])
def generate_quiz_route():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    try:
        num_mcq = int(request.form.get('num_mcq', 5))
        num_tf = int(request.form.get('num_true_false', 3))
    except ValueError:
        return jsonify({'error': 'Invalid number of questions specified'}), 400

    pdf_text = extract_text_from_pdf(file)
    if not pdf_text:
        return jsonify({'error': 'Failed to extract text from the PDF'}), 500

    prompt = f"""
    Based on the following text, generate a quiz... [rest of prompt is the same]
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
        quiz_dict = json.loads(cleaned_response)
        return jsonify(quiz_dict)
    except Exception as e:
        print(f"An error occurred during quiz generation or JSON parsing: {e}")
        return jsonify({'error': 'Failed to generate quiz from the AI model'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
