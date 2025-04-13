from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests
import os
from bs4 import BeautifulSoup
import json
from PIL import Image
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from llm_client import LLMClient

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
UPLOAD_FOLDER = os.path.join(app.static_folder)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

driver = None

def get_driver():
    global driver

    def is_alive(drv):
        try:
            drv.title
            return True
        except:
            return False

    if driver is None or not is_alive(driver):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
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
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        total_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1280, min(total_height, 3000))
        driver.save_screenshot(output_path)
    except Exception as e:
        print(f"[ERROR] Failed to capture screenshot: {e}")
        raise

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    print("Form Data:", request.form)
    print("Uploaded File:", request.files)

    input_text = request.form.get('url')
    input_image = request.files.get('image')

    if not input_text and not input_image:
        return jsonify({"error": "Please provide either a URL or an image to analyze."}), 400

    try:
        with open('prompt.json', 'r') as json_file:
            prompt_data = json.load(json_file)

        llm = LLMClient(provider="gemini")

        if input_text:
            headers = {'User-Agent': 'Mozilla/5.0'}
            screenshot_path = os.path.join(app.config['UPLOAD_FOLDER'], 'screenshot.png')
            capture_full_screenshot(input_text, screenshot_path)

            response = requests.get(input_text, headers=headers)
            if response.status_code == 403:
                return jsonify({"error": "Access to the URL is forbidden (403)."}), 403
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            html_content = str(soup)
            inline_styles = soup.find_all('style')
            css_content = "\n".join([style.get_text() for style in inline_styles])
            direction = soup.find('html').get('dir') if soup.find('html') else None
            lang = soup.find('html').get('lang') if soup.find('html') else None
            css_links = [link['href'] for link in soup.find_all('link', rel='stylesheet')]

            prompt_text = prompt_data['text_analysis_prompt'].format(
                html_content=html_content,
                css_content=css_content,
                css_links=", ".join(css_links),
                direction=direction,
                lang=lang
            )
            detailed_guidelines = prompt_data.get('detailed_guidelines', {})

            analysis_result = llm.generate_text(prompt_text, detailed_guidelines)
            return jsonify({"analysis": analysis_result, "message": "Analysis completed successfully"})

        elif input_image:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], input_image.filename)
            input_image.save(file_path)

            image_analysis_prompt = prompt_data['image_analysis_prompt']
            detailed_guidelines = json.dumps(prompt_data.get('detailed_guidelines', []))
            prompt_text = f"{image_analysis_prompt}\n\n{detailed_guidelines}"

            analysis_result = llm.generate_image_response(file_path, prompt_text)
            return jsonify({"analysis": analysis_result, "message": "Image analysis completed successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/profile')
def profile():
    return render_template('404.html')

@app.route('/history')
def history():
    return render_template('404.html')

@app.route('/logout')
def logout():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
