from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests
import os
from bs4 import BeautifulSoup
import json
from PIL import Image
import google.generativeai as genai
import imgkit
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

driver = None
# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
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
app.config['SERVER_NAME'] = 'bidibot.cs.bgu.ac.il'

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set. Please check your .env file.")

def get_driver():
    global driver

    def is_alive(drv):
        try:
            drv.title
            return True
        except WebDriverException:
            return False

    if driver is None or not is_alive(driver):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--window-size=1280,1024")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
    return driver

def capture_full_screenshot(url, output_path):
    driver = get_driver()

    try:
        start = time.time()

        driver.get(url)
        print("[TIMER] After driver.get():", round(time.time() - start, 2), "seconds")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("[TIMER] After WebDriverWait:", round(time.time() - start, 2), "seconds")

        total_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1280, min(total_height, 3000))
        driver.save_screenshot(output_path)

        print("[TIMER] After screenshot saved:", round(time.time() - start, 2), "seconds")

    except Exception as e:
        print(f"[ERROR] Failed to capture screenshot: {e}")
        raise

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    # Additional validation or processing
    # Log incoming form data and file uploads
    # print("Form Data:", request.form)
    # print("Uploaded File:", request.files)
    # Get the form data
    input_text = request.form.get('url')  # This matches the name of the URL input
    input_image = request.files.get('image')  # This is to handle image uploads

    if not input_text and not input_image:
        return jsonify({"error": "Please provide either a URL or an image to analyze."}), 400

    try:
        # Load the prompt from the JSON file (moved outside of the conditional blocks)
        with open('prompt_v3.json', 'r') as json_file:
            prompt_data = json.load(json_file)
        
        prompt_text = ""
        uploaded_file = None
        detailed_guidelines = json.dumps(prompt_data.get('detailed_guidelines', {}))
        output_example = json.dumps(prompt_data.get('output_example', {}))


        
        if input_text:
            screenshot_path = os.path.join(app.config['UPLOAD_FOLDER'], 'screenshot.png')
            capture_full_screenshot(input_text, screenshot_path)
            # Upload the screenshot to Gemini
            uploaded_file = genai.upload_file(screenshot_path)
                  
            response = requests.get(input_text, headers={'User-Agent': 'Mozilla/5.0'})

            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract HTML content, CSS, and structure for analysis
            html_content = str(soup)

            # Extract inline CSS and check if there are any right-to-left styles
            # Extract inline CSS
            inline_styles = soup.find_all('style')
            inline_css = "\n".join([style.get_text() for style in inline_styles])

            # Extract external CSS links
            css_links = [link['href'] for link in soup.find_all('link', rel='stylesheet') if link.get('href')]

            # Resolve relative URLs to absolute
            from urllib.parse import urljoin
            base_url = input_text  # the original URL you fetched
            external_css = ""

            for link in css_links:
                css_url = urljoin(base_url, link)
                try:
                    css_response = requests.get(css_url)
                    if css_response.status_code == 200:
                        external_css += f"\n/* CSS from: {css_url} */\n{css_response.text}"
                    else:
                        external_css += f"\n/* Failed to load CSS from: {css_url} (status {css_response.status_code}) */\n"
                except Exception as e:
                    external_css += f"\n/* Error fetching {css_url}: {str(e)} */\n"

            # Combine everything
            css_content = inline_css + "\n" + external_css

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

        elif input_image:
 
            # Save uploaded image
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], input_image.filename)
            input_image.save(file_path)

            # Upload image to Gemini
            uploaded_file = genai.upload_file(file_path)

            prompt_text = prompt_data['image_analysis_prompt']

        # Final call to Gemini with everything unified
        result = model.generate_content([
            uploaded_file,
            "\n\n",
            prompt_text,
            "\n\n",
            detailed_guidelines,
            "\n\n",
            output_example
        ])
        return jsonify({
            "analysis": result.text,
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
    return render_template('index.html')  # Redirect back to the homepage after logging out

if __name__ == '__main__':
    app.run(
        host='132.73.84.223',
        port=443,
        debug=True,
        ssl_context=('fullchain.pem', 'privkey.pem')  # Add the SSL certificate and key
    )
    # app.run(debug=True)