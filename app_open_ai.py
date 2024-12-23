from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import openai
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")  # Make sure to set this in your .env file

if not openai.api_key:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")

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
        # Prepare the content for the OpenAI API
        if input_text:
            prompt = f"Please analyze this web for me and tell me if it supports bidirectional layout and what to fix: {input_text}"
        else:
            prompt = "Please analyze this photo for bidirectional support."

        # Request analysis from OpenAI GPT-4 model
        completion = openai.ChatCompletion.create(
            model="gpt-4",  # Use GPT-4 model
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract the analysis result from the response
        analysis_result = completion['choices'][0]['message']['content']
        
        return jsonify({
            "analysis": analysis_result,
            "message": "Analysis completed successfully"
        })

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
    return render_template('home')  # Redirect back to the homepage after logging out

if __name__ == '__main__':
    app.run(debug=True)
