from telegram.ext import Updater, MessageHandler, Filters
from telegram import KeyboardButton, ReplyKeyboardMarkup
import logging
import os
import json

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

updater = Updater(token=os.environ["TELEGRAM_TOKEN"], use_context=True)
dispatcher = updater.dispatcher

def echo(update, context):
  print(update.to_json())

  kb = [[KeyboardButton("Where are you now?", request_location=True)]]
  
  reply_markup = ReplyKeyboardMarkup(kb)

  update.message.reply_text("Please share your location", reply_markup=reply_markup)

echo_handler = MessageHandler(Filters.text, echo)
dispatcher.add_handler(echo_handler)

def location(update, context):
  logging.info(update.to_json())

location_handler = MessageHandler(Filters.location, location)

dispatcher.add_handler(location_handler)


updater.start_polling()