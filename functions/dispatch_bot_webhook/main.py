import argparse
import googlemaps
import os
from google.cloud import firestore
import telegram
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import MessageHandler, Filters
import datetime
import json

parser = argparse.ArgumentParser(description = "Parses command")
parser.add_argument("to", type=str, nargs=1, help="the place to commute to")
parser.add_argument("max_tt", type=int, nargs=1, help="the max travel time")

gmaps = googlemaps.Client(key=os.environ["GOOGLE_MAPS_API_KEY"])
# print(gmaps_key)

db = firestore.Client()


bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])

print(str(bot))

def helper_chat_id(id):
  return u"chat_{}".format(id)

def command_setup_commute(update, command_body):
  
  chat = helper_chat_id(update.message.chat.id)

  
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

  kb = [[KeyboardButton("Click to share your location.", request_location=True)]]
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

def location_callback(update):

  # get chat id and chat from firestore

  chat = helper_chat_id(update.message.chat.id)

  snapshot = db.collection(u"commute_setup").document(chat).get().to_dict()
  
  snapshot["depart_from_latlng"] = update.message.location.to_json()
  snapshot["created"] = int(datetime.datetime.now().timestamp())

  # store snapshot in active commutes

  db.collection(u"commute_active").document(chat).set(snapshot)

  bot.send_message(chat_id = update.message.chat.id,
  text = "Thank you. Your commute is active now.",
  parse_mode = "Markdown",
  reply_markup = ReplyKeyboardRemove())

def dispatch_bot_webhook(request):

  jsn = request.json

  update = telegram.Update.de_json(request.get_json(force=True), bot)
  
  command_handler = MessageHandler(Filters.command, command_callback)
  location_handler = MessageHandler(Filters.location, location_callback)

  if command_handler.check_update(update):
    command_callback(update)

  if location_handler.check_update(update):
    location_callback(update)

  return("OK")