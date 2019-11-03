# Commute Bot

This is a Telegram bot, that can be used for helping with optimizing commute times. The use cases it solves is the following:

*As a commuter (by car), I need to know when to leave (for home/for work), so I am not stuck in traffic for longer than i find acceptable.*

The bot currently support setting up, polling the status of and canceling a commute. Commutes are active for 2hrs after creation. After that, they are deactived. The user can activate them again.

The bot is build serverless using Google Cloud Functions, Firestore and the Google Maps API (Geocoding and Directions).

## Environment setup

<https://prassanna.io/blog/pyenv-and-pipenv-for-the-perfect-python-environment/>

```{bash}
# install requirements
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
xz-utils tk-dev libffi-dev liblzma-dev libssl1.0-dev

# install pyenv https://github.com/pyenv/pyenv-installer
curl https://pyenv.run | bash

# setting up environment variables
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bashrc

# restart shell
exec $SHELL

# install python 3.7.1 (as of 10/19 gcloud functions run on this)
pyenv install 3.7.1

# activate python and install pipenv
# (note to self needs to be done for every python version)
pyenv shell 3.7.1
pyenv which python
pyenv which pip
pip install pipenv

# setting up more envirnment variables
echo 'export PIPENV_PYTHON="$PYENV_ROOT/shims/python"' >> ~/.bashrc

# install pipenv_to_requirements for exporting requirements later
pip install pipenv-to-requirements

# then install the packages
cd <into project folder>
pyenv local 3.7.1
pyenv shell 3.7.1
pyenv which python
pyenv which pipenv
pipenv shell # should setup the environment

# pipenv install flask...
```

### Environment variables

The application makes use of the following environment variables

```{}
TELEGRAM_TOKEN # The token for the telegram bot
GOOGLE_MAPS_API_KEY # API Key for the Google Maps API
COMMUTE_BOT_USERS # Comma separated list of Telegram usernames: e.g. user1,user2 to restrict access to the bot
COMMUTE_ENV=DEV # Switch between development (DEV) and production environment (PRD)
COMMUTE_BOT_WEBHOOK # Enpoint of the Telegram bot webkook; Typically something like https://<compute-region>-<project-id>.cloudfunctions.net/dispatch_bot_webhook, Only used by the deploy scripts
```

You need to create a file named `cloud-env.yml` in your root directory to store the environment variables for the Cloud Functions deployment:

```{yml}
TELEGRAM_TOKEN: your-telegram-bot-token
GOOGLE_MAPS_API_KEY: your-maps-api-key
COMMUTE_BOT_USERS: user1,user2
COMMUTE_ENV: PRD
COMMUTE_TIMEOUT: "120"
```

## TODO

- Create a python script to configure the bot --> <https://python-telegram-bot.readthedocs.io/en/stable/telegram.bot.html>
  - Webhook
  - Name
  - Commands
  - Image
- Test project this in a newly checked out directory
- Document Firestore data structure
- Refactor and move commute_monitor to separate functions; Check how to get setup and stuff working for both though
- Refactor chat_id variable names distinct between Firestore document id (chat_XXXXXXX), chat id within firestore document and telegram chat id
- Refactor get chat id always from effective chat
- Dont be surprised if sth not works when switching branches: Could be realted to having Pipfile in the repo but the venv not! Google on how to resolve this

## Commands

```{}
/commute [dest] [max_travel_time]
/cancel_commute
/update
/help
/start
```
