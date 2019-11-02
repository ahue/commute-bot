target_url="https://api.telegram.org/bot$TELEGRAM_TOKEN/setWebhook?url=$COMMUTE_BOT_WEBHOOK"
echo $target_url
curl -X GET $target_url