import unittest
from unittest.mock import patch, MagicMock
from app import app
import requests
import io

class FlaskAppTestCase(unittest.TestCase):
    """
    Test suite for Flask web application defined in app.py.
    Covers homepage accessibility, analyze endpoint with valid and invalid inputs, and system error handling.
    """

    def setUp(self):
        """
        Setup test client before each test case.
        """
        self.client = app.test_client()
        self.client.testing = True

    def test_home_page_loads(self):
        """
        Test that the homepage ('/') loads successfully with status code 200 and contains basic HTML.
        """
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<html", response.data.lower())

    @patch('app.genai.upload_file')
    @patch('app.genai.GenerativeModel.generate_content')
    @patch('app.capture_full_screenshot')
    @patch('app.requests.get')
    def test_analyze_url(self, mock_requests_get, mock_capture_screenshot, mock_generate_content, mock_upload_file):
        """
        Test the '/analyze' endpoint when a valid URL is submitted.
        Mocks external requests, Gemini model call, screenshot capture, and file upload to ensure internal logic works.
        """
        mock_upload_file.return_value = "mock_file"
        mock_generate_content.return_value.text = "Mock Gemini response"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html><head><style>body {direction: rtl;}</style></head><body></body></html>"
        mock_requests_get.return_value = mock_response

        response = self.client.post('/analyze', data={'url': 'http://example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Mock Gemini response", response.data)

    @patch('app.genai.upload_file')
    @patch('app.genai.GenerativeModel.generate_content')
    def test_analyze_image(self, mock_generate_content, mock_upload_file):
        """
        Test the '/analyze' endpoint with an image upload.
        Verifies that image handling and Gemini response logic works correctly when a file is uploaded.
        """
        mock_upload_file.return_value = "mock_image_file"
        mock_generate_content.return_value.text = "Image analysis response"

        dummy_image = (io.BytesIO(b"fake_image_data"), 'test.png')

        response = self.client.post('/analyze', content_type='multipart/form-data', data={'image': dummy_image})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Image analysis response", response.data)

    def test_analyze_missing_input(self):
        """
        Test the '/analyze' endpoint with no input data.
        Ensures the app returns a 400 error when both URL and image are missing.
        """
        response = self.client.post('/analyze', data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Please provide either a URL or an image", response.data)

    @patch('app.genai.upload_file')
    @patch('app.genai.GenerativeModel.generate_content')
    @patch('app.capture_full_screenshot')
    @patch('app.requests.get')
    def test_analyze_invalid_url(self, mock_requests_get, mock_capture_screenshot, mock_generate_content, mock_upload_file):
        """
        Test the '/analyze' endpoint with an invalid URL.
        Simulates a request error (e.g., DNS failure or malformed URL) and ensures the system handles it gracefully.
        """
        mock_requests_get.side_effect = requests.exceptions.RequestException("Invalid URL")

        data = {
            'url': 'not-a-valid-url'
        }

        response = self.client.post('/analyze', data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Invalid URL", response.data)


if __name__ == '__main__':
    unittest.main()
