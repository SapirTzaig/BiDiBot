from flask import Flask, request, jsonify, render_template, redirect, session, url_for
from dotenv import load_dotenv
import requests
import os
import logging
from requests_oauthlib import OAuth2Session

logging.basicConfig(level=logging.DEBUG)  # Set level to DEBUG for detailed logs

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Add session and cookie-related configurations
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Allow cookies to be set without HTTPS in development
    SESSION_COOKIE_HTTPONLY=True  # Ensure cookies are only accessible via HTTP (not JavaScript)
)

# Set session to use filesystem for persistence
app.config['SESSION_TYPE'] = 'filesystem'  # Store session in filesystem
app.secret_key = os.getenv("SECRET_KEY")  # Secret key for Flask sessions

# OAuth 2.0 Configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Validate environment variables
if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("CLIENT_ID or CLIENT_SECRET is not set. Please check your .env file.")

# Route to render the home page
@app.route('/')
def home():
    token = session.get('oauth_token')
    if token:
        return render_template('index.html', logged_in=True)
    else:
        return render_template('index.html', logged_in=False)


# OAuth 2.0 Login Route
@app.route('/login')
def login():
    google = OAuth2Session(CLIENT_ID, redirect_uri=url_for('callback', _external=True), scope=["openid", "https://www.googleapis.com/auth/cloud-platform"])
    authorization_url, state = google.authorization_url(AUTHORIZATION_BASE_URL, access_type="offline", prompt="consent")
    session['oauth_state'] = state
    logging.info("Redirecting to Google OAuth2 authorization URL...")
    return redirect(authorization_url)

# OAuth 2.0 Callback Route
@app.route('/callback')
def callback():
    google = OAuth2Session(CLIENT_ID, redirect_uri=url_for('callback', _external=True), state=session['oauth_state'])
    
    try:
        logging.info("Fetching OAuth token...")
        token = google.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url)
        session['oauth_token'] = token
        logging.info(f"OAuth token fetched and stored in session: {token}")
    except Exception as e:
        logging.error(f"Error fetching OAuth token: {e}")
        return jsonify({"error": "Authentication failed. Please try again."}), 500
    return redirect(url_for('home'))  # Redirect after successful authentication
    
# Unified route for analyzing either URL or image
@app.route('/analyze', methods=['POST'])
def analyze():
    # Fetch the OAuth token from the session
    token = session.get('oauth_token')
    
    if not token:
        logging.warning("OAuth token not found in session. Redirecting to login.")
        return redirect(url_for('login'))  # Redirect to login if token is missing
    
    logging.info(f"OAuth Token found: {token['access_token']}")

    # Fetch inputs from the form
    url = request.form.get('url')
    image = request.files.get('image')

    # Ensure only one input is provided
    if not url and not image:
        return jsonify({"error": "Please provide either a URL or an image"}), 400
    if url and image:
        return jsonify({"error": "Please provide only one input: either a URL or an image"}), 400

    try:
        # Prepare headers for the Gemini API request
        headers = {
            "Authorization": f"Bearer {token['access_token']}",
            "Content-Type": "application/json"
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
        if response.status_code == 200:
            response_data = response.json()
            return jsonify({
                "analysis": response_data.get("contents", []),
                "message": "Analysis successfully completed"
            })
        else:
            logging.error(f"Gemini API Error: {response.status_code} - {response.text}")
            return jsonify({"error": "API error occurred", "details": response.text}), response.status_code

    except Exception as e:
        logging.exception("An exception occurred during analysis")
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
    session.clear()  # Clear the session data
    return redirect(url_for('home'))  # Redirect back to the homepage after logging out

if __name__ == '__main__':
    app.run(debug=True)