from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests
import os
from bs4 import BeautifulSoup
import json
from PIL import Image
import pytesseract
import cv2
import numpy as np
import base64
import io
import google.generativeai as genai
from flask_sslify import SSLify

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
# sslify = SSLify(app)

# Set up the path for uploaded images
UPLOAD_FOLDER = os.path.join(app.static_folder)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set your API key here (replace 'YOUR_API_KEY' with the actual key)
API_KEY = os.getenv("GEMINI_API_KEY")
# Authenticate the API key
genai.configure(api_key=API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")
# API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# app.config['SERVER_NAME'] = 'bidibot.cs.bgu.ac.il'
# app.config['SERVER_NAME'] = 'bidibot.cs.bgu.ac.il'

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set. Please check your .env file.")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    # Additional validation or processing
    # Log incoming form data and file uploads
    print("Form Data:", request.form)
    print("Uploaded File:", request.files)
    # Get the form data
    input_text = request.form.get('url')  # This matches the name of the URL input
    input_image = request.files.get('image')  # This is to handle image uploads

    if not input_text and not input_image:
        return jsonify({"error": "Please provide either a URL or an image to analyze."}), 400

    try:
        # Load the prompt from the JSON file (moved outside of the conditional blocks)
        with open('prompt.json', 'r') as json_file:
            prompt_data = json.load(json_file)
        
        if input_text:
            # Fetch the content from the provided URL with headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            response = requests.get(input_text, headers=headers)
            if response.status_code == 403:
                return jsonify({"error": "Access to the URL is forbidden (403). Please try a different URL."}), 403
            response.raise_for_status()
            if response.status_code != 200:
                print(f"Error fetching URL: {response.status_code}")
                return jsonify({"error": f"Failed to retrieve the URL. Status code: {response.status_code}"}), 400

            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract HTML content, CSS, and structure for analysis
            html_content = str(soup)
            
            # Extract inline CSS and check if there are any right-to-left styles
            inline_styles = soup.find_all('style')
            css_content = "\n".join([style.get_text() for style in inline_styles])

            # Check for the presence of 'dir' or 'lang' attributes to identify BiDi support
            direction = soup.find('html').get('dir') if soup.find('html') else None
            lang = soup.find('html').get('lang') if soup.find('html') else None

            # Get all external CSS links that might define RTL styles
            css_links = [link['href'] for link in soup.find_all('link', rel='stylesheet')]

            # Replace placeholders in the JSON prompt with dynamic data
            prompt_text = prompt_data['text_analysis_prompt'].format(
                html_content=html_content,
                css_content=css_content,
                css_links=", ".join(css_links),
                direction=direction,
                lang=lang
            )
            detailed_guidelines = prompt_data.get('detailed_guidelines', {})

            # Construct the payload using the loaded prompt
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt_text},
                            {"text": json.dumps(detailed_guidelines)}
                        ]
                    }
                ]
            }

        elif input_image:
            # Open the image using PIL
            try:
                # Save uploaded image
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], input_image.filename)
                input_image.save(file_path)

                # Upload image to Gemini
                uploaded_file = genai.upload_file(file_path)
                prompt_text = prompt_data['image_analysis_prompt']

                # Generate content for the image
                result = model.generate_content([uploaded_file, "\n\n", prompt_text])

                return jsonify({
                    "analysis": result.text,
                    "message": "Image analysis completed successfully"
                })

            except Exception as e:
                print(f"Error during image processing: {str(e)}")
                return jsonify({"error": "Failed to process the uploaded image.", "details": str(e)}), 500

        # Set up headers
        headers = {
            "Content-Type": "application/json"
        }

        # Make the API request
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload
        )
        # Log the full response data for debugging
        #print("API Response Data:", response.json())  # Log the response to the console

        # Handle the response
        if response.status_code == 200:
            response_data = response.json()
            # Log the response structure
            #print("API Response Structure:", response_data)  # Log the actual response structure
            
            # Extract the analysis result from the response
            candidates = response_data.get("candidates", [])
            
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                
                if parts:
                    analysis_result = parts[0].get("text", "No analysis text found")
                    return jsonify({
                        "analysis": analysis_result,
                        "message": "Analysis completed successfully"
                    })
                else:
                    return jsonify({"error": "No analysis parts found."}), 500
            else:
                return jsonify({"error": "No candidates found."}), 500
        else:
            return jsonify({
                "error": f"API error occurred: {response.status_code}",
                "details": response.text
            }), response.status_code

    except Exception as e:
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
    return render_template('index.html')  # Redirect back to the homepage after logging out

if __name__ == '__main__':
    # app.run(
    #     host='132.73.84.223',
    #     port=443,
    #     debug=True,
    #     ssl_context=('fullchain.pem', 'privkey.pem')  # Add the SSL certificate and key
    # )
    app.run(debug=True)