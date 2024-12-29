from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests
import os
from bs4 import BeautifulSoup
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)

# API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set. Please check your .env file.")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    # Get the form data
    input_text = request.form.get('url')  # This matches the name of the URL input
    input_image = request.files.get('image')  # This is to handle image uploads

    if not input_text and not input_image:
        return jsonify({"error": "Please provide either a URL or an image to analyze."}), 400

    try:
        if input_text:
            # Fetch the content from the provided URL
            response = requests.get(input_text)
            if response.status_code != 200:
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

            # Combine relevant information into a payload for API analysis
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"Please analyze the following web content for bidirectional support, including its HTML structure, inline CSS, and external stylesheets.\n\nHTML Content:\n{html_content}\n\nInline CSS:\n{css_content}\n\nExternal CSS Links:\n{', '.join(css_links)}\n\nDirectionality: {direction}\nLanguage: {lang}"}
                        ]
                    }
                ]
            }

        else:
            # In case of image, provide analysis text
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": "Please analyze this photo for bidirectional support."}
                        ]
                    }
                ]
            }

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
        print("API Response Data:", response.json())  # Log the response to the console

        # Handle the response
        if response.status_code == 200:
            response_data = response.json()
            # Log the response structure
            print("API Response Structure:", response_data)  # Log the actual response structure
            
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
    app.run(debug=True)
