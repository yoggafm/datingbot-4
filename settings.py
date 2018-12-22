import os

FLASK_DEBUG = os.environ.get('FLASK_DEBUG', False)
TOKEN = os.environ.get('TOKEN', '')
GROUP_ID = os.environ.get('GROUP_ID', '')
CONFIRM_TOKEN = os.environ.get('CONFIRM_TOKEN', '')
PORT = os.environ.get('PORT', 8080)
VK_API_VERSION = os.environ.get('VK_API_VERSION', '5.50')
QNA_FILE = os.environ.get('QNA_FILE', 'qna.json')
