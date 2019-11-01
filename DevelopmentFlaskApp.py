# DevelopmentFlaskApp.py 
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "serviceaccount.json"

from flask import Flask, request, render_template, send_from_directory
from functions.dispatch_bot_webhook import main as f_dispatch_bot_webhook

app = Flask(__name__)

@app.route("/dispatch_bot_webhook", methods = ['POST'])
def flask_dispatch_bot_webhook():
  return f_dispatch_bot_webhook.dispatch_bot_webhook(request)

@app.route("/commute_monitor", methods = ['GET'])
def flask_commute_monitor():
  return f_dispatch_bot_webhook.commute_monitor(request)

if __name__ == "__main__":
  app.run(debug=True)