# DevelopmentFlaskApp.py 
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "serviceaccount.json"

from flask import Flask, request, render_template, send_from_directory
from functions.dispatch_bot_webhook import main as f_dispatch_bot_webhook

app = Flask(__name__)

@app.route("/dispatch_bot_webhook", methods = ['POST'])
def flask_dispatch_bot_webhook():
  f_dispatch_bot_webhook.dispatch_bot_webhook(request)
  return "OK", 200

@app.route("/commute_monitor", methods = ['GET'])
def flask_commute_monitor():
  f_dispatch_bot_webhook.commute_monitor(request)
  return "OK", 200

if __name__ == "__main__":
  app.run(debug=True)