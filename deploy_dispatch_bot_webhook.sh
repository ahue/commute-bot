#/bin/sh

# TODO: Remove --allow-unauthenticated 
# execute this script in the root directory of the project


# export environment variables
. setup_env.sh

# generate requirements
pipenv run pipenv_to_requirements -f
cp requirements.txt functions/dispatch_bot_webhook/requirements.txt

cur_dir=($PWD);
cd functions/dispatch_bot_webhook;

# deploy
gcloud functions deploy dispatch_bot_webhook \
  --env-vars-file ../../cloud_env.yml \
  --runtime python37 \
  --trigger-http \
  --region europe-west1 \
  --entry-point dispatch_bot_webhook \
  --memory 128MB \
  --allow-unauthenticated 

# set the webhook new
target_url="https://api.telegram.org/bot$TELEGRAM_TOKEN/setWebhook?url=$COMMUTE_BOT_WEBHOOK"
echo $target_url
curl -X GET $target_url

cd $cur_dir;