import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
import fitz

load_dotenv()
app = Flask(__name__)

# Allow requests from your Netlify site
CORS(app, resources={r"/api/*": {"origins": "https://astounding-figolla-545b70.netlify.app"}})

try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found.")
    genai.configure(api_key=api_key)
    print("Gemini API configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

def extract_text_from_pdf(pdf_file):
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

@app.route('/api/generate', methods=['POST'])
def generate_quiz_route():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    num_mcq = request.form.get('num_mcq', 5, type=int)
    num_tf = request.form.get('num_true_false', 3, type=int)

    pdf_text = extract_text_from_pdf(file)
    if not pdf_text or len(pdf_text) < 50: # Check if text is too short
         return jsonify({'error': 'Could not extract enough text from PDF.'}), 500

    prompt = f"""
    Based on the following text, generate a quiz with exactly {num_mcq} multiple-choice questions
    and {num_tf} true/false questions.
    TEXT: "{pdf_text[:4000]}"
    RESPONSE FORMAT: Return ONLY a single, valid JSON object. Do not include any other text, markdown, or explanations. The JSON object must have two keys: "mcqs" and "true_false".
    - "mcqs" must be a list of objects, each with "question" (string), "options" (list of 4 strings), and "correct_answer" (string).
    - "true_false" must be a list of objects, each with "question" (string) and "correct_answer" (boolean true/false).
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # --- THIS IS THE CRITICAL NEW PART ---
        # Print the raw response from the AI so we can see it in the logs
        print("--- RAW AI RESPONSE ---")
        print(response.text)
        print("-----------------------")
        
        # Find the start and end of the JSON object
        start = response.text.find('{')
        end = response.text.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in AI response.")

        cleaned_response = response.text[start:end]
        
        quiz_dict = json.loads(cleaned_response)
        return jsonify(quiz_dict)
        
    except Exception as e:
        print(f"AN ERROR OCCURRED: {e}")
        return jsonify({'error': f'Failed to parse AI response: {e}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
