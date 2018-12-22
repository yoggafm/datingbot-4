import vk
import qna
from settings import VK_API_VERSION

session = vk.Session()
api = vk.API(session, v=VK_API_VERSION)

def send_message(user_id, token, message, attachment=""):
	api.messages.send(access_token=token, user_id=str(user_id), message=message, attachment=attachment)
