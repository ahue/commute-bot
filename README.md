# Commute Bot

## The most simple thing

1. (complete) command on commute is received
2. command is stored

1. commute scheduler calls check function regularly
2. check function sends info to bot

## GCP

- Project commute-bot

Communication:

Telegram Commands -> Telegram Webhook -> Google Cloud Functions
GCP Cloud Scheduler -> GCP Cloud Functions (regular commute check) -> Telegram
Firebase to store commutes

Data structure see data structure.yml

Dialogue



# Commands

```
/commute [dest]
```


# Dialogue 