from telegram.ext import Updater, MessageHandler, Filters, CallbackQueryHandler
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
  update.message.reply_text(update.message.text)

echo_handler = MessageHandler(Filters.text, echo)
dispatcher.add_handler(echo_handler)

def callback(update, context):
  print(update.callback_query.data)

callback_handler = CallbackQueryHandler(callback)
dispatcher.add_handler(callback_handler)

def location(update, context):
  logging.info(update.to_json())

location_handler = MessageHandler(Filters.location, location)

dispatcher.add_handler(location_handler)


updater.start_polling()