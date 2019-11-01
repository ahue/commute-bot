#/bin/sh

# TODO: Remove --allow-unauthenticated 

# generate requirements
pipenv run pipenv_to_requirements -f
cp requirements.txt functions/dispatch_bot_webhook/requirements.txt

cur_dir=($PWD);
cd functions/dispatch_bot_webhook;

gcloud functions deploy dispatch_bot_webhook \
  --env-vars-file ../../cloud_env.yml \
  --runtime python37 \
  --trigger-http \
  --region europe-west1 \
  --entry-point dispatch_bot_webhook \
  --memory 128MB \
  --allow-unauthenticated 

cd $cur_dir;