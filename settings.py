import os

FLASK_DEBUG = os.environ.get('FLASK_DEBUG', False)
TOKEN = os.environ.get('TOKEN', '5728932780:AAFQ-Hz0QAQHIV7j7s8hiH0n6Fj9adfKfhQ')
GROUP_ID = os.environ.get('GROUP_ID', 'Kebugaran2023')
CONFIRM_TOKEN = os.environ.get('CONFIRM_TOKEN', '5728932780:AAFQ-Hz0QAQHIV7j7s8hiH0n6Fj9adfKfhQ')
PORT = os.environ.get('PORT', 8080)
VK_API_VERSION = os.environ.get('VK_API_VERSION', '5.50')
VK_API_URL = os.environ.get('VK_API_URL', 'https://api.vk.com/method/')
QNA_FILE = os.environ.get('QNA_FILE', 'qna.json')
DB_FILE = os.environ.get('DB_FILE', '.db')
COMMANDS_KEYBOARD = {
    "one_time":False,
    "buttons": [
      [{
        "action": {
          "type": "text",
          "payload": "{\"button\": \"1\"}",
          "label": "Регистрация"
        },
        "color": "default"
      },
     {
        "action": {
          "type": "text",
          "payload": "{\"button\": \"2\"}",
          "label": "Поиск"
        },
        "color": "default"
      }],
      [{
        "action": {
          "type": "text",
          "payload": "{\"button\": \"3\"}",
          "label": "Удалить свою анкету"
        },
        "color": "default"
      },
     {
        "action": {
          "type": "text",
          "payload": "{\"button\": \"4\"}",
          "label": "Помощь"
        },
        "color": "primary"
      }]
    ]
}
