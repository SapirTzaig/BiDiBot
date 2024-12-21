from flask import Flask, request, jsonify, render_template, redirect, session
from dotenv import load_dotenv
import requests
import os
import logging

logging.basicConfig(level=logging.DEBUG)  # Set level to DEBUG for detailed logs


# Load environment variables
load_dotenv()

app = Flask(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validate the API key
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set. Please check your .env file.")

# Gemini API URL
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Route to render the home page
@app.route('/')
def home():
    return render_template('index.html')

# Unified route for analyzing either URL or image
@app.route('/analyze', methods=['POST'])
def analyze():
    # Fetch inputs from the form
    url = request.form.get('url')
    image = request.files.get('image')

    # Ensure only one input is provided
    if not url and not image:
        return jsonify({"error": "Please provide either a URL or an image"}), 400
    if url and image:
        return jsonify({"error": "Please provide only one input: either a URL or an image"}), 400

    try:
        # Prepare payload and headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GEMINI_API_KEY}"
        }

        # Handle URL analysis
        if url:
            payload = {
                "prompt": {
                    "text": f"Analyze the following URL for bidirectional support and features: {url}"
                }
            }
            response = requests.post(GEMINI_API_URL, headers=headers, json=payload)

        # Handle image analysis
        elif image:
            # Save the image temporarily
            image_path = os.path.join("uploads", image.filename)
            os.makedirs("uploads", exist_ok=True)  # Ensure the uploads directory exists
            image.save(image_path)

            payload = {
                "prompt": {
                    "text": f"Analyze the following image located at {image_path} for bidirectional support and features."
                }
            }
            response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
            os.remove(image_path)  # Clean up the uploaded image file

        # Process Gemini API response
        response_data = response.json()
        if response.status_code == 200:
            return jsonify({
                "analysis": response_data.get("contents", []),
                "message": "Analysis successfully completed"
            })
        else:
            logging.error(f"Response Status: {response.status_code}")
            logging.error(f"Response Headers: {response.headers}")
            logging.error(f"Response Body: {response.text}")
            logging.error(f"API Error: {response_data}")  # Log API error details
            return jsonify({"error": response_data.get("error", "Unknown error occurred")}), response.status_code

    except Exception as e:
        logging.exception("An exception occurred during analysis")  # Log the full stack trace
        return jsonify({"error": str(e)}), 500

@app.route('/profile')
def profile():
    # Logic to render the user profile page
    return render_template('404.html')  # Ensure you have a 'profile.html' template

@app.route('/history')
def history():
    # Logic to render the user's history page
    return render_template('404.html')  # Ensure you have a 'history.html' template

@app.route('/logout')
def logout():
    session.clear()  # Assuming you're using Flask sessions
    return redirect('index.html')  # Redirect back to the homepage after logging out

if __name__ == '__main__':
    app.run(debug=True)
