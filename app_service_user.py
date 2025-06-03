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
import htmlmin
from csscompressor import compress

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
# app.config['SERVER_NAME'] = 'bidibot.cs.bgu.ac.il'

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
        chrome_options.add_argument("--enable-unsafe-swiftshader")

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
    input_text = request.form.get('url')
    input_image = request.files.get('image')

    if not input_text and not input_image:
        return jsonify({"error": "Please provide either a URL or an image to analyze."}), 400

    try:
        # Load both JSON files
        with open('user_prompt.json', 'r', encoding='utf-8') as user_file:
            user_prompt_data = json.load(user_file).get('user_prompt', {})
        
        with open('service_prompt.json', 'r', encoding='utf-8') as service_file:
            service_prompt_data = json.load(service_file).get('service_prompt', {})

        prompt_text = ""
        uploaded_file = None

        # Extract relevant parts from user_prompt.json for placeholders and details
        detailed_guidelines = json.dumps(user_prompt_data.get('detailed_guidelines', {}))
        output_example = json.dumps(user_prompt_data.get('output_example', {}))
        another_output_example = json.dumps(user_prompt_data.get('another_output_example', {}))

        if input_text:
            screenshot_path = os.path.join(app.config['UPLOAD_FOLDER'], 'screenshot.png')
            capture_full_screenshot(input_text, screenshot_path)
            uploaded_file = genai.upload_file(screenshot_path)

            response = requests.get(input_text, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.content, 'html.parser')

            html_content = str(soup)
            html_content = htmlmin.minify(html_content, remove_comments=True, remove_empty_space=True)

            inline_styles = soup.find_all('style')
            inline_css = "\n".join([style.get_text() for style in inline_styles])
            inline_css = compress(inline_css)

            css_links = [link['href'] for link in soup.find_all('link', rel='stylesheet') if link.get('href')]
            css_links = css_links[:3]

            from urllib.parse import urljoin
            base_url = input_text
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

            external_css = compress(external_css)
            css_content = inline_css + "\n" + external_css
            MAX_CSS_LENGTH = 10000
            css_content = css_content[:MAX_CSS_LENGTH]

            direction = soup.find('html').get('dir') if soup.find('html') else None
            lang = soup.find('html').get('lang') if soup.find('html') else None

            css_links_str = ", ".join(css_links)

            prompt_template = (
                "Analyze the following UI information based on the provided guidelines.\n\n"
                "HTML:\n{html_content}\n\n"
                "CSS:\n{css_content}\n\n"
                "CSS Links:\n{css_links}\n\n"
                "Direction: {direction}\n"
                "Language: {lang}\n\n"
            )

            prompt_text = prompt_template.format(
                html_content=html_content,
                css_content=css_content,
                css_links=css_links_str,
                direction=direction,
                lang=lang
            )

        elif input_image:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], input_image.filename)
            input_image.save(file_path)
            uploaded_file = genai.upload_file(file_path)
            # Use image_analysis_prompt from user_prompt.json
            prompt_text = user_prompt_data.get('image_analysis_prompt', '')

        # Compose final prompt for Gemini combining user and service JSON data as string
        # This mirrors your previous structure but now uses parts from both files.
        final_prompt = (
            prompt_text
            + "\n\n" + detailed_guidelines
            + "\n\n" + output_example
            + "\n\n" + json.dumps(service_prompt_data)  # adding service prompt data in string form
        )

        token_estimate = len(final_prompt.split())
        print(f"[DEBUG] Estimated token usage: {token_estimate}")

        # Gemini call expects a list of strings and files, keep same structure you had before
        result = model.generate_content([
            uploaded_file,
            "\n\n",
            final_prompt
        ])

        return jsonify({
            "analysis": result.text,
            "message": "Analysis completed successfully"
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Invalid URL: {str(e)}"}), 400

    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
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

    app.run(host="127.0.0.1", port=5000, debug=True)
