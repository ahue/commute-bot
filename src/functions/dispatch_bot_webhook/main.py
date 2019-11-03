import argparse
import googlemaps
import os
from google.cloud import firestore
import telegram
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, Filters, CallbackQueryHandler
import datetime
import json
import numpy as np

# parser = argparse.ArgumentParser(description = "Parses command")
# parser.add_argument("to", type=str, nargs=1, help="the place to commute to")
# parser.add_argument("max_tt", type=int, nargs=1, help="the max travel time")

gmaps = googlemaps.Client(key=os.environ["GOOGLE_MAPS_API_KEY"])
# print(gmaps_key)

db = firestore.Client()


class BotClient:
  """ Singleton for the bot client """
  instance = None
  def __init__(self, *args, **kwargs):
    if not BotClient.instance:
      BotClient.instance = telegram.Bot(*args, **kwargs)
    
  def __getattr__(self, name):
    return getattr(self.instance, name)

bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])

# print(str(bot))

KEYB_BTN_REQUEST_STATUS = "Request update on commute time 🔄"
KEYB_BTN_CANCEL_COMMUTE = "Cancel commute ❌"
COMMUTE_ENV = os.environ["COMMUTE_ENV"]
COMMUTE_ENV_PRD = "PRD"
COMMUTE_ENV_DEV = "DEV"
try:
  COMMUTE_TIMEOUT = int(os.environ["COMMUTE_TIMEOUT"])
except:
  COMMUTE_TIMEOUT = 120

MAPS_URL = "https://www.google.com/maps/dir/?api=1&orgin={}&destination={}&travelmode=driving"

def helper_chat_id(id: int):
  """
  prepends an telegra_cat_id with "chat_" to have a common id for Firestore documents 
  """
  return u"chat_{}".format(id)

def helper_concat_latlng(dictionary):
  """ Concats lat and long from a dictionary by comma """
  res = "{},{}".format(dictionary["latitude"],dictionary["longitude"])
  print(res)
  return res

def helper_maps_url_reply_markup(origin, destination):
  """ Returns a formatted url to Google Maps directions with provided origin and destination """
  maps_url = MAPS_URL.format(
    origin,
    destination
  )
  # TODO: Replace whitespaces in URL!

  ilb = [[InlineKeyboardButton("Open Google Maps 🗺️",url=maps_url)]]
  reply_markup = InlineKeyboardMarkup(ilb)  
  return reply_markup

def frmt_ttime(seconds):
  """
    Nicely formats an amout of seconds in hrs in minutes
    5231 ->  1h 27min
  """
  mins = round(seconds/60) 
  hrs_out = int(mins / 60)
  mins_out = int(mins - hrs_out * 60)
  if hrs_out > 0:
    if mins_out > 0:
      return "{}h {}min".format(hrs_out, mins_out)
    else:
      return "{}h".format(hrs_out)
  else:
    return "{}min".format(mins_out)

def frmt_addr(input):
  """
    Nicely formats an address retrieved from google geocoder
    e.g. Kurfürstendamm 10, Berlin, Germany --> Kurfürstendamm 10 Germany
  """
  # TODO: Add a google maps link to the address
  # TODO: Remove plz
  return ",".join(input.split(",")[0:-1]).replace(",","").strip()

def command_setup_commute(update, command_body):
  
  chat = helper_chat_id(update.message.chat.id)

  
  # command should look like "Trudering 40", which means to Trudering in 40mins
  # args = parser.parse_args(command_body.strip().split(" "))

  # to = args.to[0]
  # max_tt = int(args.max_tt[0])

  to = " ".join(command_body.split(" ")[0:-1])
  max_tt = int(command_body.split(" ")[-1]) * 60 # seconds

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
    text = "Please share your location, so I know where you depart.",
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

def activate_commute_msg(commute):
  print("activate_commute_msg")
  
  chat_id = commute["chat"]

  kb = [[KeyboardButton(KEYB_BTN_REQUEST_STATUS)],
    [KeyboardButton(KEYB_BTN_CANCEL_COMMUTE)]]
  reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
  
  # Add Keyboard via fake message and delete the message
  msg = bot.send_message(chat_id = chat_id, text = ".", reply_markup=reply_markup)
  bot.delete_message(chat_id = chat_id, message_id=msg.message_id)


  reply_markup = helper_maps_url_reply_markup(
    helper_concat_latlng(commute["depart_from_latlng"]),
    commute["commute_to"]
  )

  bot.send_message(chat_id = chat_id,
  text = "Thank you. Your commute to *{}* is active now.".format(frmt_addr(commute["commute_to"])),
  parse_mode = "Markdown",
  reply_markup = reply_markup)

  duration = check_current_duration(commute)
  single_status_update(commute, duration)

def location_callback(update):

  # get chat id and chat from firestore

  chat = helper_chat_id(update.message.chat.id)

  commute = db.collection(u"commute_setup").document(chat).get().to_dict()
  
  commute["depart_from_latlng"] = json.loads(update.message.location.to_json())
  commute["created"] = int(datetime.datetime.now().timestamp())

  # Add Keyboard via fake message and delete the message
  msg = bot.send_message(chat_id = commute["chat"], text = ".", reply_markup=ReplyKeyboardRemove())
  bot.delete_message(chat_id = commute["chat"], message_id=msg.message_id)

  # TODO: Check minimal travel time and alert if requested time is lower than that
  check_reasonable_travel_time(commute)

  return

def text_callback(update):

  handler = {
    KEYB_BTN_CANCEL_COMMUTE: cancel_commute,
    KEYB_BTN_REQUEST_STATUS: single_status_update_btn
  }.get(update.message.text, default_text_handler)

  handler(update)

def callback_query_callback(update):

  print("callback_query_callback")

  callback_data_prefix = update.callback_query.data.split("|")[0]
  try:
    callback_data_payload = json.loads(update.callback_query.data.split("|")[1])
  except:
    callback_data_payload = None

  handler = {
    "reactivate_last_commute": reactivate_last_commute,
    "set_max_travel_time": set_max_travel_time
  }.get(callback_data_prefix, "Ohoh!")

  handler(update, callback_data_payload)

def cancel_commute(update, *args):

  chat_id = update.message.chat.id
  chat = helper_chat_id(chat_id)

  doc_ref = db.collection(u"commute_active").document(chat)

  bot.send_message(chat_id = chat_id, 
    text="Canceled your commute to *{}*".format(frmt_addr(doc_ref.get().get("commute_to"))),
    parse_mode = "Markdown", 
    reply_markup = ReplyKeyboardRemove())

  doc_ref.delete()

def reactivate_last_commute(update, *args):
  print("reactivate_last_commute")
  # get last commute from archive
  # TODO: Remove the working info from document (e.g. duration probes, current traveltime, min traveltime)
  doc_snp = next(db.collection(u"commute_archive").where("chat", "==", update.effective_chat.id).order_by("created").limit(1).stream()).to_dict()
  
  doc_snp["created"] = int(datetime.datetime.now().timestamp())

  # set to active
  chat = helper_chat_id(update.effective_chat.id)
  db.collection(u"commute_active").document(chat).set(doc_snp)
  print("after write")
  # inform the user
  activate_commute_msg(doc_snp)

def set_max_travel_time(update, payload):

  chat = helper_chat_id(update.effective_chat.id)
  
  commute = db.collection(u"commute_setup").document(chat).get().to_dict()
  
  commute["max_travel_time"] = payload["max_travel_time"]
  # check reasonable travel time
  check_reasonable_travel_time(commute)

def check_reasonable_travel_time(commute):

  chat = helper_chat_id(commute["chat"])

  today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
  next_sunday_night = int((today + datetime.timedelta(days = (7 - today.weekday()) % 7 ) + datetime.timedelta(hours = 1)
  ).timestamp())

  try:
    duration_min = commute["duration_min"]
  except KeyError:
    directions = gmaps.directions(origin = helper_concat_latlng(commute["depart_from_latlng"]),
      destination = commute["commute_to"],
      traffic_model = "optimistic",
      departure_time = next_sunday_night
    )

    duration_min = directions[0]["legs"][0]["duration"]["value"]
    commute["duration_min"] = duration_min

  try:
    duration_current = commute["duration_probes"][-1]["duration"]
  except KeyError:
    duration = check_current_duration(commute)
    duration_current = duration["value"]  

    duration_current = directions[0]["legs"][0]["duration"]["value"]
    commute["duration_probes"] = [
      {
        "timestamp": int(datetime.datetime.now().timestamp()),
        "duration": duration_current
      }
    ]

  if COMMUTE_ENV == COMMUTE_ENV_DEV:
    duration_current = 1.5 * duration_min

  # schneller wirds nicht, braucht kein commute, fahr jetzt los
  if float(duration_min) / float(duration_current) > 0.97:
    bot.send_message(chat_id = commute["chat"],
      text = "The current estimated travel time of *{}* is already very close to the minimal time to *{}*. You better depart now. No need for a commute reminder.".format(
        frmt_ttime(duration_current), 
        frmt_addr(commute["commute_to"])),
      parse_mode = "Markdown"
    )

    # remove reminder from setup
    return False

  if duration_min > commute["max_travel_time"]:

    db.collection(u"commute_setup").document(chat).set(commute)

    # set up reasonable buttons
    print(duration_current)
    print(duration_min)

    steps = np.asarray((float(duration_current) - 
      np.array([0.2, 0.4, 0.8]) * (duration_current - duration_min)) 
    , dtype=int)

    emojis = ["🐌","🐇","🚀"]
    ilb = [[InlineKeyboardButton("{} {}".format(e, frmt_ttime(s)), 
      callback_data=u"set_max_travel_time|{{\"max_travel_time\" : {} }}".format(s)) for s, e in zip(steps, emojis)]]

    reply_markup = InlineKeyboardMarkup(ilb)  

    # send 
    bot.send_message(chat_id = commute["chat"],
      text = "Sorry! Your wished travel time of *{}* is too optimistic. Current travel time is *{}*. Lowest estimated travel time to *{}* is *{}*. Want to choose a more realistic one from below?".format(
        frmt_ttime(commute["max_travel_time"]),
        frmt_ttime(duration_current),
        frmt_addr(commute["commute_to"]),
        frmt_ttime(duration_min)
      ), parse_mode = "Markdown",
      reply_markup = reply_markup)
    
    return False

  # store snapshot in active commutes
  db.collection(u"commute_active").document(chat).set(commute)
  
  activate_commute_msg(commute)

  if COMMUTE_ENV == COMMUTE_ENV_DEV:
    db.collection(u"commute_setup").document(chat).delete()

def single_status_update_btn(update, *args):
  # TODO: Refactor naming of function, since its not a button anymore
  chat = helper_chat_id(update.effective_chat.id)
  commute = db.collection(u"commute_active").document(chat).get().to_dict()
  
  duration = check_current_duration(commute)
  single_status_update(commute, duration)

def check_current_duration(commute):

  directions = gmaps.directions(origin=helper_concat_latlng(commute["depart_from_latlng"]),
    destination=commute["commute_to"]
    )

  duration = {
    "text": directions[0]["legs"][0]["duration"]["text"],
    "value": directions[0]["legs"][0]["duration"]["value"]
  }

  chat = helper_chat_id(commute["chat"])
  doc_ref = db.collection(u"commute_active").document(chat)
  doc_ref.set({
    "duration_probes": doc_ref.get().get("duration_probes").append({
      "timestamp": int(datetime.datetime.now().timestamp()),
      "duration": duration["value"]
    })
  })  

  return duration

def single_status_update(commute, duration):
  """ Get and send a status update for a given commute """

  # print("Got directions")
  # print(str(directions))

  db.collection(u"commute_active").document(helper_chat_id(commute["chat"])).set({
    "last_status_update": int(datetime.datetime.now().timestamp())
  })

  reply_markup = helper_maps_url_reply_markup(
    helper_concat_latlng(commute["depart_from_latlng"]),
    commute["commute_to"]
  )

  bot.send_message(chat_id = commute["chat"],
    text = "Currently, commute to *{}* will take *{}*.".format(
      frmt_addr(commute["commute_to"]), 
      frmt_ttime(duration["value"])),
    parse_mode = "Markdown",
    reply_markup = reply_markup)

def default_text_handler(update):
  """ Sends a default message back to the bot """
  bot.send_message(chat_id = update.effective_chat.id, 
    text = "Sorry, I didn't get that...")

def dispatch_bot_webhook(request):

  update = telegram.Update.de_json(request.get_json(force=True), bot)
  print(update)

  # Only allow defined users to use the bot
  if update.effective_user.username not in os.environ["COMMUTE_BOT_USERS"].split(","):
    return ("Nothing to gain here")

  print("passed user check")
  callback_query_filter = CallbackQueryHandler(callback_query_callback)

  handler = None
  try:
    if Filters.command.filter(update.message):
      print("command_handler")
      handler = command_callback
  except AttributeError:
    None

  try:
    if Filters.location.filter(update.message):
      print("location_handler")
      handler = location_callback
  except AttributeError:
    None

  try:
    if Filters.text.filter(update.message):
      print("text_handler")
      handler =text_callback
  except AttributeError:
    None

  try:
    if callback_query_filter.check_update(update):
      print("callback_query_filter")
      handler = callback_query_callback
  except AttributeError:
    None

  handler(update)

def check_active_commutes():
  # get active commutes
  for doc_ref in db.collection(u"commute_active").stream():

    commute = doc_ref.to_dict()


    # TODO: Think about passing arround document references instead of dictionaries... but think hard
    duration = check_current_duration(commute)
    
    try:
      last_status_update = commute["last_status_update"]
    except KeyError:
      last_status_update = 0

    ts_now = datetime.datetime.now().timestamp()

    # Compute wheter commute time changed more than probe timestamps 
    # e.g. difference between probes in time: 300sec, difference in commute-time 400sec
    try:
      change =  (ts_now - commute["duration_probes"][-1]["timestamp"] < 
        abs(duration["value"] - commute["duration_probes"][-1]["duration"]))
    except KeyError:
      change = False

    # TODO: compute trend if there is enough data (at least 2 probes and one current)
    # TODO: if negative extrapolate when desired duration is reached
    # TODO: inform user if increasing or decreasing more than 5mins
    # TODO: make flexible threhold configurable

    if (change or
      duration["value"] * 0.95 < commute["max_travel_time"] or # close to desired commute_time 
      last_status_update < int(ts_now) - 900): # didn't hear from the bot longer that 15mins
          
      single_status_update(commute, duration)

def remove_outdated_commutes():
  """ remove outdated commutes after timeout period """
  
  # delete_thres = int(datetime.datetime.now().timestamp())
  delete_thres = int(datetime.datetime.now().timestamp() - 3600* float(COMMUTE_TIMEOUT)/60)

  for doc_snp in db.collection(u"commute_active").where("created", "<=", delete_thres).stream():
     
    db.collection(u"commute_archive").add(doc_snp.to_dict())

    # TODO: Implement step by step new commute setup
    ilb = [[InlineKeyboardButton("Restart this commute 🔁",callback_data="reactivate_last_commute"),
      #InlineKeyboardButton("Start a new commute ▶️", callback_data="start_new_commute")
      ]]
    reply_markup = InlineKeyboardMarkup(ilb)  

    bot.send_message(chat_id=doc_snp.get("chat"), 
      text="Your commute to *{}* timed out. Feel free to start a new one.".format(
        frmt_addr(doc_snp.get("commute_to"))
      ),
      parse_mode = "Markdown",
      reply_markup = reply_markup
    )

    if COMMUTE_ENV == COMMUTE_ENV_PRD:
      db.collection(u"commute_active").document(doc_snp.id).delete()

def commute_monitor(request):
  """
    Get regularly called by a cron job and
      a) removes outdated commutes
      b) checks active commutes and sends infos to user
  """
  check_active_commutes()
  remove_outdated_commutes()

  return "OK", 200