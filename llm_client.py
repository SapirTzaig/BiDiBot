import os
import json
import google.generativeai as genai

class LLMClient:
    def __init__(self, provider="gemini"):
        self.provider = provider
        if self.provider == "gemini":
            self.api_key = os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not set in environment variables.")
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            raise NotImplementedError(f"Provider '{self.provider}' not supported yet.")

    def generate_text(self, prompt_text, detailed_guidelines):
        try:
            response = self.model.generate_content([
                {"text": prompt_text},
                {"text": json.dumps(detailed_guidelines)}
            ])
            return response.text
        except Exception as e:
            raise RuntimeError(f"Error generating text: {str(e)}")

    def generate_image_response(self, image_path, prompt_text):
        try:
            uploaded_file = genai.upload_file(image_path)
            result = self.model.generate_content([uploaded_file, "\n\n", prompt_text])
            return result.text
        except Exception as e:
            raise RuntimeError(f"Error generating image response: {str(e)}")
