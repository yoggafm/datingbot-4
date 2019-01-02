import requests
from flask_api import status
from sqlite3 import IntegrityError, OperationalError, ProgrammingError
import vk
from db import qna
from settings import FLASK_DEBUG, TOKEN, VK_API_VERSION, VK_API_URL
if FLASK_DEBUG: from pprint import pprint

session = vk.Session()
api = vk.API(session, v=VK_API_VERSION)

def send_message(user_id, token, message, attachment=""):
    api.messages.send(access_token=token, user_id=str(user_id), message=message,
                      attachment=attachment)

class registration(object):
    "Methods related to dating registration"

    def __init__(self, user_id, dbc, start=True):
        self.user_id = user_id
        self.dbc = dbc
        self.step = 0
        if start: self.start()

    def __repr__(self):
        return "uuid {0} ({1} step)".format(self.user_id, self.step)

    def start(self):
        # init cache
        first, last = self.get_name_from_vk()
        self.dbc.cache[self.user_id] = {
            "first_name": first,
            "last_name": last
        }
        # ask first question
        self.ask_current_question()

    def ask_current_question(self, prefix='', postfix='', attachment=''):
        question = qna[self.step]['question']
        options = qna[self.step]['opts']
        if type(options) == list:
            options = '\n'.join(options)
        elif not options:
            options = ''
        msg = '{0}\n{1}\n{2}\n{3}'.format(prefix, question, options, postfix)
        if FLASK_DEBUG: print(msg)
        send_message(str(self.user_id), TOKEN, msg, attachment)

    def get_name_from_vk(self):
        url = "{}users.get".format(VK_API_URL)
        params = {
            "user_id":self.user_id,
            "fields":["first_name","last_name"],
            "access_token": TOKEN,
            "v":VK_API_VERSION
        }
        try:
            resp = requests.get(url, params=params).json()
            if FLASK_DEBUG:
                print("GET " + url)
                pprint(params)
                pprint(resp)
            if 'response' in resp:
                data = resp['response'][0]
                return data["first_name"], data["last_name"]
            return None, None
        except Exception as e:
            if FLASK_DEBUG: print(e)
            return None, None

    def validate_answer(self, body):
        "Validate user's answer to reistration questions"
        options = qna[self.step]['opts']
        answer = col = ''
        if options:
            # options
            for opt in options:
                if opt.startswith(body) or opt[3:].startswith(body):
                    answer = opt[:1]
                    col = qna[self.step]['user_field']
                    break
        else:
            # free text/photo
            answer = body
            col = qna[self.step]['user_field']
        if options and answer == '':
            send_message(str(self.user_id), TOKEN,\
                'Выбери, пожалуйста, из представленных '\
                'вариантов:{}\nМожешь просто скопипастить'\
                ' желаемый вариант и отправить, либо '\
                'только его начало.\nПример: для выборa '\
                'варианта "1) Брно" можно отправить: '
                '"1) Брно", "Брно", или "1", "1)", "1) Б" и т.д)'.format(
                    '\n'.join(options)))
            if FLASK_DEBUG: print("Illigitimate answer {}".format(body))
            return status.HTTP_404_NOT_FOUND
        if FLASK_DEBUG: print("You chose variant \"{0}\"".format(answer))
        return answer

    def process_answer(self, answer):
        "Execute actions required after question has been answered"
        # save to cache
        col = qna[self.step]['user_field']
        self.dbc.cache[self.user_id][col] = answer
        # next step
        self.step += 1

    def view(self):
        "View user's name and photo"
        first_name = self.dbc.cache[self.user_id]['first_name']
        photo = self.dbc.cache[self.user_id]['photo']
        city_id = self.dbc.cache[self.user_id]['city_id']
        self.dbc.connect()
        city = self.dbc.get_name("cities", city_id)
        self.dbc.close()
        if FLASK_DEBUG: print("{0}, {1}".format(first_name, city))
        return "{0}, {1}".format(first_name, city), photo 
        
    def commit(self):
        "Commit changes from cache to db"
        try:
            self.dbc.connect()
            self.dbc.create_user(self.user_id)
            self.dbc.save(self.user_id)
        except ProgrammingError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id), TOKEN,
                'Похоже, ты нашел ошибку у меня в коде, мой друг! ' \
                'Срочно напиши сюда (id218786773) с как можно более подробным описанием проблемы.')
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        except OperationalError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id), TOKEN,
                'Произошла ошибка при сохранении. Попробуй заново через какое-то время.')
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        except IntegrityError as err:
            if FLASK_DEBUG:
                print("user {} is already registered".format(self.user_id))
            send_message(str(self.user_id), TOKEN,
                'Твоя анкета уже есть в базе данных!.')
            # do not return error
        if FLASK_DEBUG: print("End of registration.")
        return status.HTTP_200_OK

    def abort(self):
        "Abort registration"
        if FLASK_DEBUG: print("End of registration - aborted.")
        send_message(str(self.user_id), TOKEN, "Ну и пошел нахуй тогда")
        return status.HTTP_200_OK

    def edit(self):
        #TODO: edit
        if FLASK_DEBUG: print("Updating.")
        send_message(str(self.user_id), TOKEN, "Not Implemented")
        return status.HTTP_501_NOT_IMPLEMENTED

