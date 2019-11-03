#/bin/sh

# TODO: Remove --allow-unauthenticated 
# execute this script in the root directory of the project

# generate requirements
pipenv run pipenv_to_requirements -f
cp requirements.txt src/functions/dispatch_bot_webhook/requirements.txt

cur_dir=($PWD);
cd src/functions/dispatch_bot_webhook;
  
gcloud functions deploy commute_monitor \
  --env-vars-file ../../cloud_env.yml \
  --runtime python37 \
  --trigger-http \
  --region europe-west1 \
  --entry-point commute_monitor \
  --memory 128MB \
  --allow-unauthenticated

cd $cur_dir;