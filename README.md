# BiDiBot
 Automatic Bidirectional Analyzing Tool

# Abstract
Our project presents an innovative solution to a common yet under-addressed challenge in user interface (UI) design: identifying and resolving bidirectional issues caused by the combination of different languages and writing directions (e.g., Hebrew or Arabic, which are written from right to left, and English, which is written from left to right). 

# Features
- Analyze UI from a website URL or an uploaded image
- Detect issues in bidirectional (BiDi) interfaces
- Use LLMs (Gemini 1.5) for smart analysis
- Provide actionable design recommendations
- Export results to PDF
- Simple, user-friendly interface
- Support for UX roles (e.g., developer, designer)

# Technologies Used
- Python & Flask – Backend server
- JavaScript (Vanilla) – Frontend interactivity
- HTML/CSS – UI structure and styling
- Gemini LLM (via Google Generative AI) – AI model for analysis
- BeautifulSoup + Selenium – HTML & structure scraping
- jsPDF – PDF generation in browser

# How It Works
1. User inputs a URL or uploads a screenshot.
2. Backend captures the HTML/CSS and screenshot.
3. Data is cleaned and compressed, then formatted into a prompt that contains guidlines.
4. Prompt is sent to Gemini LLM for analysis.
5. Response is parsed and shown on the frontend.
6. User can export the result as a professional PDF.

# Credits
Developed by: Sapir Tzaig, David Miliov, Liron Shamen
Supervisors: Prof. Noam Tractinsky, Dr. Dennis Klimov, Ms. Yulia Goldenberg
