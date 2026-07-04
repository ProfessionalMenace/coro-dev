import json

with open("./config/config.json", "r") as config:
	_config_data = json.load(config)

with open("./config/secrets.json", "r") as secrets:
  _secrets_data = json.load(secrets)

TOKEN = _secrets_data["BOT TOKEN"]
CURRENT_HOST = _secrets_data["CURRENT HOST"]

BOT_COLOR = _config_data["BOT COLOR"]
SERVER_ID = int(_config_data["SERVER ID"])
MOD_ROLE_ID = int(_config_data["MOD ROLE ID"])
LOG_CHANNEL_ID = int(_config_data["LOG CHANNEL ID"])