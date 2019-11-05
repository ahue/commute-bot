import pytest
import mock
import unittest
import os
import json
from copy import copy
import datetime

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "serviceaccount.json"

import src.functions.dispatch_bot_webhook.main as subject

def test_helper_chat_id():
  assert subject.helper_chat_id(1234) == "chat_1234"

def test_helper_concat_latlng():
  data = {
    "latitude": 48.139260,
    "longitude": 11.563405
  }
  assert subject.helper_concat_latlng(data) == "48.13926,11.563405"

class MapsUrlHelperReplyMarkupTestCase(unittest.TestCase):

  @mock.patch("src.functions.dispatch_bot_webhook.main.InlineKeyboardMarkup")
  @mock.patch("src.functions.dispatch_bot_webhook.main.InlineKeyboardButton")
  def test_helper_maps_url_reply_markup(self, mock_ikb, mock_ikm):

    print(subject.helper_maps_url_reply_markup("from here", "to there"))

    url = "https://www.google.com/maps/dir/?api=1&orgin=from here&destination=to there&travelmode=driving"

    mock_ikb.assert_called_with("Open Google Maps 🗺️", url=url)
    mock_ikm.assert_called_once()

def test_frmt_ttime():
  assert subject.frmt_ttime(60) == "1min"
  assert subject.frmt_ttime(61) == "1min"
  assert subject.frmt_ttime(89) == "1min"
  assert subject.frmt_ttime(90) == "2min"
  assert subject.frmt_ttime(3600) == "1h"
  assert subject.frmt_ttime(3601) == "1h"
  assert subject.frmt_ttime(3660) == "1h 1min"

def test_frmt_addr():
  assert subject.frmt_addr("Kurfürstendamm 10, Berlin, Germany") == "Kurfürstendamm 10 Berlin"
  assert subject.frmt_addr("Kurfürstendamm 10, 88888 Berlin, Germany") == "Kurfürstendamm 10 88888 Berlin"

# class CheckReasonableTravelTime(unittest.TestCase):

#   @mock.patch("src.functions.dispatch_bot_webhook.main.googlemaps.Client.directions")
#   @mock.patch("src.functions.dispatch_bot_webhook.main.telegram.Bot.send_message")
#   def test_check_reasonable_travel_time(self, mock_send_message, mock_directions):
    
#     commute = {
#       "chat": 100,
#       "commute_to": "Frankfurt",
#       "depart_from_latlng": {
#         "latitude": 48.139260,
#         "longitude": 11.563405
#       }
#     }

#     subject.check_reasonable_travel_time(commute)

#     assert int(mock_directions.call_count) == 2

class CheckCurrentDurationTestCase(unittest.TestCase):

  @mock.patch("src.functions.dispatch_bot_webhook.main.googlemaps.Client.directions")
  @mock.patch("src.functions.dispatch_bot_webhook.main.firestore.Client.collection")
  def test_check_current_duration(self,mock_collection, mock_directions):

    mock_directions.return_value = [{
        "legs": [{
          "end_address": "Destination Adress",
          "duration": {
            "text": "Trip duration",
            "value": 1000
          }
        }]
      }]

    commute = {
      "chat": 100,
      "commute_to": "Frankfurt",
      "depart_from_latlng": {
        "latitude": 48.139260,
        "longitude": 11.563405
      }
    }

    subject.check_current_duration(commute)

    mock_collection.assert_called_once_with(u"commute_active")


class CheckActiveCommutesTestCase(unittest.TestCase):

  @mock.patch("src.functions.dispatch_bot_webhook.main.firestore.Query.stream")
  @mock.patch("src.functions.dispatch_bot_webhook.main.check_current_duration")
  @mock.patch("src.functions.dispatch_bot_webhook.main.single_status_update")
  @mock.patch("src.functions.dispatch_bot_webhook.main.firestore.DocumentSnapshot.to_dict")
  def test_check_active_commutes(self, mock_to_dict, mock_single_status_update, 
    mock_check_current_duration, mock_stream):

    doc_snp = mock.Mock()
       
    mock_stream.return_value = [doc_snp, copy(doc_snp)]
    doc_snp.to_dict.return_value

    doc_snp.to_dict.return_value = {
      "chat": 100,
      "commute_to": "Frankfurt",
      "max_travel_time": 900
    }

    mock_check_current_duration.return_value = {
      "text": "Some time",
      "value": 3600
    }

    subject.check_active_commutes()

    assert mock_single_status_update.call_count == 2
    
    # Test with last status update 
    doc_snp.to_dict.return_value["last_status_update"] = datetime.datetime.now().timestamp()
    
    subject.check_active_commutes()
    assert mock_single_status_update.call_count == 2

    # Test with duration probes
    # timedifference is 900 but duration difference is 0 --> no call
    doc_snp.to_dict.return_value["duration_probes"] = [{
      "timestamp": datetime.datetime.now().timestamp() - 900,
      "duration": 3600
    }]

    subject.check_active_commutes()
    assert mock_single_status_update.call_count == 2

    # time difference is 900 and duration abs difference of duration is >900 --> should call
    # TODO: edge cases
    doc_snp.to_dict.return_value["duration_probes"][0]["duration"] = 2600
    subject.check_active_commutes()
    assert mock_single_status_update.call_count == 4    

    # time difference is 900 and duration abs difference of duration is >900 --> should call
    doc_snp.to_dict.return_value["duration_probes"][0]["duration"] = 4700
    subject.check_active_commutes()
    assert mock_single_status_update.call_count == 6    

    del doc_snp.to_dict.return_value["duration_probes"]

    # Current duration is 900 which is 900*0.97 < max_travel_time --> should call
    mock_check_current_duration.return_value["value"] = 900
    subject.check_active_commutes()
    assert mock_single_status_update.call_count == 8    


class RemoveOutdatedCommutesTestCase(unittest.TestCase):


  @mock.patch("src.functions.dispatch_bot_webhook.main.firestore.Query.stream")
  @mock.patch("src.functions.dispatch_bot_webhook.main.firestore.CollectionReference.add")
  @mock.patch("src.functions.dispatch_bot_webhook.main.firestore.DocumentReference.delete")
  @mock.patch("src.functions.dispatch_bot_webhook.main.telegram.Bot.send_message")
  def test_remove_outdated_commutes(self, mock_send_message, mock_delete, mock_add, mock_stream):

    doc_snp = mock.Mock()
    doc_snp.to_dict.return_value = {}
    doc_snp.get.side_effect = {"chat": 100, "commute_to": "Berlin"}.get
    
    mock_stream.return_value = [doc_snp, copy(doc_snp)]
    
    subject.remove_outdated_commutes()

    mock_stream.assert_called_once()
    assert mock_add.call_count == 2
    assert mock_send_message.call_count == 2
    mock_delete.assert_not_called() # since we are in dev


class CommuteMonitorTestCase(unittest.TestCase):

  @mock.patch("src.functions.dispatch_bot_webhook.main.check_active_commutes")
  @mock.patch("src.functions.dispatch_bot_webhook.main.remove_outdated_commutes")
  def test_commute_monitor(self, mock_remove_outdated_commutes, mock_check_active_commutes):

    subject.commute_monitor(None)

    mock_remove_outdated_commutes.assert_called_once()
    mock_check_active_commutes.assert_called_once()

class SingleStatusUpdateBtnTestCase(unittest.TestCase):
  
  @mock.patch("src.functions.dispatch_bot_webhook.main.firestore.Client.collection")
  @mock.patch("src.functions.dispatch_bot_webhook.main.single_status_update")
  @mock.patch("src.functions.dispatch_bot_webhook.main.check_current_duration")
  def test_single_status_update_btn(self, mock_check_current_duration, 
    mock_single_status_update, mock_collection):
    
    update = mock.Mock()
    update.effective_chat.id = 100

    mock_check_current_duration.return_value = {
      "text": "Some text",
      "value": 1000
    }

    subject.single_status_update_btn(update)
    mock_collection.assert_called_once()
    mock_check_current_duration.assert_called_once()
    mock_single_status_update.assert_called_once()

class SingleStatusUpdateTestCase(unittest.TestCase):
  # @mock.patch("src.functions.dispatch_bot_webhook.main.googlemaps.Client.directions")
  @mock.patch("src.functions.dispatch_bot_webhook.main.telegram.Bot.send_message")
  def test_single_status_update(self, mock_send_message):

    commute = {
      "chat": 100,
      "commute_to": "Frankfurt",
      "depart_from_latlng": {
        "latitude": 48.139260,
        "longitude": 11.563405
      }
    }



    subject.single_status_update(commute, {"text": "Some text", "value": 1000})

    # mock_directions.assert_called_once()
    mock_send_message.assert_called_once()

class SendStartMessageTestCase(unittest.TestCase):
  
  @mock.patch("src.functions.dispatch_bot_webhook.main.telegram.Bot.send_message")
  @mock.patch("src.functions.dispatch_bot_webhook.main.send_help_message")
  def test_send_start_message(self, mock_send_help_message, mock_send_message):

    update = mock.Mock()
    update.effective_chat.id = 100
    subject.send_start_message(update)
    mock_send_message.assert_called_once()
    mock_send_help_message.assert_called_once()

class SendHelpMessageTestCase(unittest.TestCase):
  
  @mock.patch("src.functions.dispatch_bot_webhook.main.telegram.Bot.send_message")
  def test_send_help_message(self, mock_send_message):

    update = mock.Mock()
    update.effective_chat.id = 100
    subject.send_help_message(update)
    mock_send_message.assert_called_once()

class SendPrivacyMessageTestCase(unittest.TestCase):
  
  @mock.patch("src.functions.dispatch_bot_webhook.main.telegram.Bot.send_message")
  def test_send_privacy_message(self, mock_send_message):

    update = mock.Mock()
    update.effective_chat.id = 100
    subject.send_privacy_message(update)
    mock_send_message.assert_called_once()

class DefaultTextHandlerTestCase(unittest.TestCase):
  
  @mock.patch("src.functions.dispatch_bot_webhook.main.telegram.Bot.send_message")
  def test_default_text_handler(self, mock_send_message):

    update = mock.Mock()
    update.effective_chat.id = 100
    subject.default_text_handler(update)
    mock_send_message.assert_called_once_with(chat_id = update.effective_chat.id, text = "Sorry, I didn't get that...")

class DispatchBotWebhookTextCase(unittest.TestCase):

  @mock.patch("src.functions.dispatch_bot_webhook.main.callback_query_callback")
  @mock.patch("src.functions.dispatch_bot_webhook.main.location_callback")
  @mock.patch("src.functions.dispatch_bot_webhook.main.text_callback")
  @mock.patch("src.functions.dispatch_bot_webhook.main.command_callback")
  @mock.patch("src.functions.dispatch_bot_webhook.main.os")
  def test_dispatch_bot_webhook(self, mock_os, mock_command_callback, mock_text_callback, mock_location_callback, mock_callback_query_callback):

    data = json.loads("""{
      "update_id": 123456789,
      "message": {
          "message_id": 80,
          "date": 1572622280,
          "chat": {
              "id": 123456789,
              "type": "private",
              "username": "ausername",
              "first_name": "A",
              "last_name": "Hue"
          },
          "text": "/commute Berlin 30",
          "entities": [],
          "caption_entities": [],
          "photo": [],
          "new_chat_members": [],
          "new_chat_photo": [],
          "delete_chat_photo": false,
          "group_chat_created": false,
          "supergroup_chat_created": false,
          "channel_chat_created": false,
          "from": {
              "id": 123456789,
              "first_name": "A",
              "is_bot": false,
              "last_name": "Hue",
              "username": "ausername",
              "language_code": "de"
          }
      },
      "_effective_user": {
          "id": 123456789,
          "first_name": "A",
          "is_bot": false,
          "last_name": "Hue",
          "username": "ausername",
          "language_code": "de"
      },
      "_effective_chat": {
          "id": 123456789,
          "type": "private",
          "username": "ausername",
          "first_name": "A",
          "last_name": "Hue"
      },
      "_effective_message": {
          "message_id": 80,
          "date": 1572622280,
          "chat": {
              "id": 123456789,
              "type": "private",
              "username": "ausername",
              "first_name": "A",
              "last_name": "Hue"
          },
          "text": "huhu",
          "entities": [],
          "caption_entities": [],
          "photo": [],
          "new_chat_members": [],
          "new_chat_photo": [],
          "delete_chat_photo": false,
          "group_chat_created": false,
          "supergroup_chat_created": false,
          "channel_chat_created": false,
          "from": {
              "id": 123456789,
              "first_name": "A",
              "is_bot": false,
              "last_name": "Hue",
              "username": "ausername",
              "language_code": "de"
          }
      }
    }""") 

    req = mock.Mock(get_json=mock.Mock(return_value = data), args=data)

    mock_os.environ = {
      "COMMUTE_BOT_USERS": ""
    }

    assert subject.dispatch_bot_webhook(req) == "Nothing to gain here"  

    mock_os.environ = {
      "COMMUTE_BOT_USERS": "ausername"
    }  

    # Test command
    data["message"]["text"] = "/command"
    req = mock.Mock(get_json=mock.Mock(return_value = data), args=data)
    subject.dispatch_bot_webhook(req)
    mock_command_callback.assert_called_once()

    # Test text
    data["message"]["text"] = "Any other text"
    req = mock.Mock(get_json=mock.Mock(return_value = data), args=data)
    subject.dispatch_bot_webhook(req)
    mock_text_callback.assert_called_once()

    # Test location
    data["message"]["text"] = ""
    data["message"]["location"] = {
      "longitude": 11.563405,
      "latitude": 48.139260
    }
    req = mock.Mock(get_json=mock.Mock(return_value = data), args=data)
    subject.dispatch_bot_webhook(req)
    mock_location_callback.assert_called_once()

    data = json.loads("""{
      "update_id": 862109540,
      "callback_query": {
        "id": "2503834263126265946",
        "chat_instance": "8585815830327687897",
        "message": {
          "message_id": 139,
          "date": 1572634093,
          "chat": {
            "id": 123456789,
            "type": "private",
            "username": "ausername",
            "first_name": "A",
            "last_name": "Hue"
          },
          "text": "Your commute to Berlin, Germany timed out. Feel free to start a new one.",
          "entities": [
            {
              "type": "bold",
              "offset": 16,
              "length": 15
            }
          ],
          "caption_entities": [],
          "photo": [],
          "new_chat_members": [],
          "new_chat_photo": [],
          "delete_chat_photo": false,
          "group_chat_created": false,
          "supergroup_chat_created": false,
          "channel_chat_created": false,
          "reply_markup": {
            "inline_keyboard": [
              [
                {
                  "text": "Restart this commute \ud83d\udd01",
                  "callback_data": "reactivate_last_commute"
                },
                {
                  "text": "Start a new commute \u25b6\ufe0f",
                  "callback_data": "start_new_commute"
                }
              ]
            ]
          },
          "from": {
            "id": 987654321,
            "first_name": "Commute Bot",
            "is_bot": true,
            "username": "AhuCommuteBot"
          }
        },
        "data": "reactivate_last_commute",
        "from": {
          "id": 123456789,
          "first_name": "A",
          "is_bot": false,
          "last_name": "Hue",
          "username": "ausername",
          "language_code": "de"
        }
      },
      "_effective_user": {
        "id": 123456789,
        "first_name": "A",
        "is_bot": false,
        "last_name": "Hue",
        "username": "ausername",
        "language_code": "de"
      },
      "_effective_chat": {
        "id": 123456789,
        "type": "private",
        "username": "ausername",
        "first_name": "A",
        "last_name": "Hue"
      },
      "_effective_message": {
        "message_id": 139,
        "date": 1572634093,
        "chat": {
          "id": 123456789,
          "type": "private",
          "username": "ausername",
          "first_name": "A",
          "last_name": "Hue"
        },
        "text": "Your commute to Berlin, Germany timed out. Feel free to start a new one.",
        "entities": [
          {
            "type": "bold",
            "offset": 16,
            "length": 15
          }
        ],
        "caption_entities": [],
        "photo": [],
        "new_chat_members": [],
        "new_chat_photo": [],
        "delete_chat_photo": false,
        "group_chat_created": false,
        "supergroup_chat_created": false,
        "channel_chat_created": false,
        "reply_markup": {
          "inline_keyboard": [
            [
              {
                "text": "Restart this commute \ud83d\udd01",
                "callback_data": "reactivate_last_commute"
              },
              {
                "text": "Start a new commute \u25b6\ufe0f",
                "callback_data": "start_new_commute"
              }
            ]
          ]
        },
        "from": {
          "id": 987654321,
          "first_name": "Commute Bot",
          "is_bot": true,
          "username": "AhuCommuteBot"
        }
      }
    }"""
    )
    req = mock.Mock(get_json=mock.Mock(return_value = data), args=data)
    subject.dispatch_bot_webhook(req)
    mock_callback_query_callback.assert_called_once()



    