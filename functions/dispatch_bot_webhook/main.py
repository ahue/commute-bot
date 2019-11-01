import argparse
import googlemaps
import os
from google.cloud import firestore
import telegram
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, Filters
import datetime
import json

# parser = argparse.ArgumentParser(description = "Parses command")
# parser.add_argument("to", type=str, nargs=1, help="the place to commute to")
# parser.add_argument("max_tt", type=int, nargs=1, help="the max travel time")

gmaps = googlemaps.Client(key=os.environ["GOOGLE_MAPS_API_KEY"])
# print(gmaps_key)

db = firestore.Client()


bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])

# print(str(bot))

KEYB_BTN_REQUEST_STATUS = "Request update on commute time 🔄"
KEYB_BTN_CANCEL_COMMUTE = "Cancel commute ❌"

MAPS_URL = "https://www.google.com/maps/dir/?api=1&orgin={}&destination={}&travelmode=driving"

def helper_chat_id(id):
  return u"chat_{}".format(id)

def helper_concat_latlng(dictionary):
  res = "{},{}".format(dictionary["latitude"],dictionary["longitude"])
  print(res)
  return res

def helper_maps_url_reply_markup(origin, destination):
  maps_url = MAPS_URL.format(
    origin,
    destination
  )

  ilb = [[InlineKeyboardButton("Open Google Maps 🗺️",url=maps_url)]]
  reply_markup = InlineKeyboardMarkup(ilb)  
  return reply_markup


def command_setup_commute(update, command_body):
  
  chat = helper_chat_id(update.message.chat.id)

  
  # command should look like "Trudering 40", which means to Trudering in 40mins
  # args = parser.parse_args(command_body.strip().split(" "))

  # to = args.to[0]
  # max_tt = int(args.max_tt[0])

  to = " ".join(command_body.split(" ")[0:-1])
  max_tt = int(command_body.split(" ")[-1])

  # Lookup in maps 
  geocode = gmaps.geocode(to)
  to = geocode[0]["formatted_address"]

  # store info in firestore
  doc_ref = db.collection(u"commute_setup").document(chat)
  doc_ref.set({
    u"chat": update.message.chat.id,
    u"commute_to": to,
    u"max_travel_time": max_tt
  })

  # request current geolocation from user

  # TODO: Add button to cancel
  kb = [[KeyboardButton("Tap to share your location. 📍", request_location=True)]]
  reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)

  print(update.message.chat.id)

  bot.send_message(chat_id = update.message.chat.id,
    text = "Please share your location",
    parse_mode = "Markdown",
    reply_markup = reply_markup)
  # update.message.reply_text("Please share your location", reply_markup=reply_markup)

  return(("OK", 200))

def command_callback(update):
  # TODO: Add the commands to the telegram bot
  command = update.message.text 

  command_prefix = command.split(" ")[0].strip()
  command_body = command.replace(command_prefix, "").strip()
  print(command_prefix)
  print(command_body)
  handler = {
    "/commute": command_setup_commute,
    "/cancel_commute": cancel_commute,
    "/update": single_status_update_btn
  }.get(command_prefix, "Ohoh!")

  print(str(handler))
  handler(update, command_body)

def location_callback(update):

  # get chat id and chat from firestore

  chat = helper_chat_id(update.message.chat.id)

  snapshot = db.collection(u"commute_setup").document(chat).get().to_dict()
  
  snapshot["depart_from_latlng"] = json.loads(update.message.location.to_json())
  snapshot["created"] = int(datetime.datetime.now().timestamp())

  # TODO: Check minimal travel time and alert if requested time is lower than that
  # store snapshot in active commutes

  db.collection(u"commute_active").document(chat).set(snapshot)
  
  kb = [[KeyboardButton(KEYB_BTN_REQUEST_STATUS)],
    [KeyboardButton(KEYB_BTN_CANCEL_COMMUTE)]]
  reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
  
  # Add Keyboard via fake message and delete the message
  msg = bot.send_message(chat_id = update.message.chat.id, text = ".", reply_markup=reply_markup)
  bot.delete_message(chat_id = update.message.chat.id, message_id=msg.message_id)


  reply_markup = helper_maps_url_reply_markup(
    helper_concat_latlng(snapshot["depart_from_latlng"]),
    snapshot["commute_to"]
  )

  bot.send_message(chat_id = update.message.chat.id,
  text = "Thank you. Your commute is active now.",
  parse_mode = "Markdown",
  reply_markup = reply_markup)

  #db.collection(u"commute_setup").document(chat).delete()

def text_callback(update):

  handler = {
    KEYB_BTN_CANCEL_COMMUTE: cancel_commute,
    KEYB_BTN_REQUEST_STATUS: single_status_update_btn
  }.get(update.message.text, default_text_handler)

  handler(update)

def cancel_commute(update, *args):

  chat_id = update.message.chat.id
  chat = helper_chat_id(chat_id)

  doc_ref = db.collection(u"commute_active").document(chat)

  bot.send_message(chat_id = chat_id, 
    text="Canceled your commute to *{}*".format(doc_ref.get().get("commute_to")),
    parse_mode = "Markdown", 
    reply_markup = ReplyKeyboardRemove())

  doc_ref.delete()

def single_status_update_btn(update, *args):
  # TODO: Refactor naming of function
  chat = helper_chat_id(update.message.chat.id)
  commute = db.collection(u"commute_active").document(chat).get().to_dict()
  single_status_update(commute)

def single_status_update(commute):

  directions = gmaps.directions(origin=helper_concat_latlng(commute["depart_from_latlng"]),
      destination=commute["commute_to"]
      )

  # print("Got directions")
  # print(str(directions))

  reply_markup = helper_maps_url_reply_markup(
    helper_concat_latlng(commute["depart_from_latlng"]),
    commute["commute_to"]
  )

  bot.send_message(chat_id = commute["chat"],
    text = "Currently, commute to *{}* will take *{}*.".format(directions[0]["legs"][0]["end_address"], directions[0]["legs"][0]["duration"]["text"]),
    parse_mode = "Markdown",
    reply_markup = reply_markup)

def default_text_handler(update):
  bot.send_message(chat_id = update.message.chat.id, 
    text = "Sorry, I didn't get that...")

def dispatch_bot_webhook(request):

  jsn = request.json

  update = telegram.Update.de_json(request.get_json(force=True), bot)
  print(update)

  # Only allow defined users to use the bot
  user_handler = MessageHandler(Filters.user(
    username=os.environ["COMMUTE_BOT_USERS"].split(",")
  ), None)
  if not user_handler.check_update(update):
    return ("Nothing to gain here")

  command_handler = MessageHandler(Filters.command, command_callback)
  location_handler = MessageHandler(Filters.location, location_callback)
  text_handler = MessageHandler(Filters.text, text_callback)

  if command_handler.check_update(update):
    command_callback(update)

  if location_handler.check_update(update):
    location_callback(update)

  if text_handler.check_update(update):
    text_callback(update)

def commute_monitor(request):
  """
    Get regularly called by a cron job and
      a) removes outdated commutes
      b) checks active commutes and sends infos to user
  """

  # get active commutes
  for doc_ref in db.collection(u"commute_active").stream():

    commute = doc_ref.to_dict()

    single_status_update(commute)

  #TODO: Store if time is decreasing or increasing and inform user
  #TODO: Only send messages when travel time is below threshold, but send a status update now and then
  #TODO: Think about haveing a keyboard ready to stop or request status

  #TODO: Think about using traffic_model="pessimistic"

  
  #TODO: remove outdated commutes
  #delete_thres = int(datetime.datetime.now().timestamp())
  delete_thres = int(datetime.datetime.now().timestamp()) - 3600*2

  for doc_snp in db.collection(u"commute_active").where("created", "<=", delete_thres).select(["chat"]).stream():
    db.collection(u"commute_active").document(doc_snp.id).delete()


  return(str(directions))