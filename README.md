# Commute Bot

## Environment setup

TODO: Test this in a newly checked out directory!

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

## Commands

```
/commute [dest] [max_travel_time]
/cancel_commute
/update
/help
/start
```

## Dialogue
