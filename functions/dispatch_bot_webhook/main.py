import argparse
import googlemaps
import os
from google.cloud import firestore
import telegram
from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import MessageHandler, Filters

parser = argparse.ArgumentParser(description = "Parses command")
parser.add_argument("to", type=str, nargs=1, help="the place to commute to")
parser.add_argument("max_tt", type=int, nargs=1, help="the max travel time")

gmaps = googlemaps.Client(key=os.environ["GOOGLE_MAPS_API_KEY"])
# print(gmaps_key)

db = firestore.Client()


bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])

print(str(bot))

def command_setup_commute(update, command_body):
  
  chat = u"chat_{}".format(update.message.chat.id)

  
  # command should look like "Trudering 40", which means to Trudering in 40mins
  args = parser.parse_args(command_body.strip().split(" "))

  to = args.to[0]
  max_tt = int(args.max_tt[0])

  # Lookup in maps 
  geocode = gmaps.geocode(to)
  to = geocode[0]["formatted_address"]

  # store info in firestore
  doc_ref = db.collection(u"commute_setup").document(chat)
  doc_ref.set({
    u"chat": chat,
    u"commute_to": to,
    u"max_travel_time": max_tt
  })

  # request current geolocation from user

  kb = [[KeyboardButton("Where are you now?", request_location=True)]]
  reply_markup = ReplyKeyboardMarkup(kb)

  print(update.message.chat.id)

  bot.send_message(chat_id = update.message.chat.id,
    text = "Please share your location",
    parse_mode = "Markdown",
    reply_markup = reply_markup)
  # update.message.reply_text("Please share your location", reply_markup=reply_markup)

def command_callback(update):
  
  command = update.message.text 

  command_prefix = command.split(" ")[0].strip()
  command_body = command.replace(command_prefix, "").strip()
  print(command_prefix)
  print(command_body)
  handler = {
    "/commute": command_setup_commute
  }.get(command_prefix, "Ohoh!")

  print(str(handler))
  handler(update, command_body)

def dispatch_bot_webhook(request):

  jsn = request.json

  update = telegram.Update.de_json(request.get_json(force=True), bot)
  
  command_handler = MessageHandler(Filters.command, command_callback)

  if command_handler.check_update(update):
    command_callback(update)

  return("OK")