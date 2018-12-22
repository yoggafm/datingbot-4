import vk
import qna
from settings import VK_API_VERSION, NEWUSR

session = vk.Session()
api = vk.API(session, v=VK_API_VERSION)

def send_message(user_id, token, message, attachment=""):
	api.messages.send(access_token=token, user_id=str(user_id), message=message, attachment=attachment)

def get_answer(body):
	message = "Прости, не понимаю тебя. Напиши '/bothelp', чтобы узнать мои команды"
	process = getattr(qna, body)  # FIXME except AttributeError as 'now such commands, available are: 
	message = process()  #FIXME error handling
	return message

def create_answer(data, token):
   user_id = data['user_id']
   message = get_answer(data['body'].lower())
   vkapi.send_message(user_id, token, message, attachment)
