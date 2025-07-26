from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Nexus Elite Bot is alive and running! 🚀"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "Nexus Elite"}

def run():
    port = int(os.environ.get("PORT", 8080))  # Render uses $PORT
    app.run(host='0.0.0.0', port=port)  # Must bind to 0.0.0.0

def keep_alive():
    Thread(target=run, daemon=True).start() 