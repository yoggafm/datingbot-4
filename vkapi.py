import requests
import random
import re
import string
import os
from flask_api import status
from sqlite3 import IntegrityError, OperationalError, ProgrammingError
import vk
from db import qna
from settings import FLASK_DEBUG, TOKEN, VK_API_VERSION, VK_API_URL
if FLASK_DEBUG: from pprint import pprint

session = vk.Session()
api = vk.API(session, access_token=TOKEN, v=VK_API_VERSION)

def send_message(user_id, message, attachment=""):
    api.messages.send(user_id=str(user_id), message=message,
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
        send_message(str(self.user_id), msg, attachment)

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

    def upload_photo(self, url):
        # download
        path = ''.join(random.choices(string.ascii_letters + string.digits,
            k=16)) + '.jpg'
        resp = requests.get(url)
        if resp.status_code == status.HTTP_200_OK:
            img = resp.raw.read()
            with open(path,'wb') as f:
                for chunk in resp:
                    f.write(chunk)
        else:
            return status.HTTP_500_INTERNAL_SERVER_ERROR

        # upload to server
        upload_url = api.photos.getMessagesUploadServer(
            peer_id=self.user_id)['upload_url']
        if FLASK_DEBUG: print('upload_url = {}'.format(upload_url))
        resp = requests.post(upload_url, files={'photo': open(path, 'rb')})
        if resp.status_code != status.HTTP_200_OK:
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        params = resp.json()
        if FLASK_DEBUG: print('params = {}'.format(params))
        resp = api.photos.saveMessagesPhoto(**params)
        if not (len(resp) and 'owner_id' in resp[0] and 'id' in resp[0]):
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        owner_id = resp[0]['owner_id']
        photo_id = resp[0]['id']
        # delete photo from our server
        if os.path.exists(path):
            os.remove(path)
        return "photo{0}_{1}".format(owner_id, photo_id)

    def validate_answer(self, body=None, photo=None):
        "Validate user's answer to reistration questions"
        options = qna[self.step]['opts']
        answer = col = ''
        if body:
            if options:
                # options
                for opt in options:
                    if opt.startswith(body) or opt[3:].startswith(body):
                        answer = opt[:1]
                        col = qna[self.step]['user_field']
                        break
                if answer == '':
                    send_message(str(self.user_id),
                        'Выбери, пожалуйста, из представленных '\
                        'вариантов:{}\nМожешь просто скопипастить'\
                        ' желаемый вариант и отправить, либо '\
                        'только его начало.\nПример: для выборa '\
                        'варианта "1) Брно" можно отправить: '
                        '"1) Брно", "Брно", или "1", "1)", "1) Б" '\
                        'и т.д) '.format('\n'.join(options)))
                    if FLASK_DEBUG: print("Illigitimate answer {}".format(body))
                    return status.HTTP_404_NOT_FOUND
            else:
                # free text
                answer = body
                col = qna[self.step]['user_field']
        if photo:
            if options:
                send_message(str(self.user_id),
                    'Выбери, пожалуйста, из представленных '\
                    'вариантов:{}\nМожешь просто скопипастить'\
                    ' желаемый вариант и отправить, либо '\
                    'только его начало.\nПример: для выборa '\
                    'варианта "1) Брно" можно отправить: '
                    '"1) Брно", "Брно", или "1", "1)", "1) Б" '\
                    'и т.д) '.format('\n'.join(options)))
            # photo
            if type(photo) != dict:
                if FLASK_DEBUG: print("Bad photo {}".format(photo))
                return status.HTTP_404_NOT_FOUND
            photo_keys = [ key for key in photo if key.startswith('photo_') ]
            if not len(photo_keys):
                if FLASK_DEBUG: print("Bad photo {}".format(photo))
                return status.HTTP_404_NOT_FOUND
            max_key = 'photo_' + str(max([int(key.strip('photo_')) \
                for key in photo_keys]))
            # upload to vk, returns photo<owner_id>_<photo_id>
            answer = self.upload_photo(photo[max_key])
 
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
        description = self.dbc.cache[self.user_id]['description']
        city_id = self.dbc.cache[self.user_id]['city_id']
        self.dbc.connect()
        city = self.dbc.get_name("cities", city_id)
        self.dbc.close()
        text = "{0}, {1}\n{2}".format(first_name, city, description)
        if FLASK_DEBUG: print(text); print(photo)
        return text, photo 
        
    def commit(self):
        "Commit changes from cache to db"
        try:
            self.dbc.connect()
            self.dbc.create_user(self.user_id)
            self.dbc.save(self.user_id)
       #TODO error handlers
        except ProgrammingError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id),
                'Похоже, ты нашел ошибку у меня в коде, мой друг! ' \
                'Срочно напиши сюда (id218786773) с как можно более подробным описанием проблемы.')
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        except OperationalError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id),
                'Произошла ошибка при сохранении. Попробуй заново через какое-то время.')
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        except IntegrityError as err:
            if FLASK_DEBUG:
                print("user {} is already registered".format(self.user_id))
            send_message(str(self.user_id), 'Твоя анкета уже есть в базе данных!.')
            # do not return error
        if FLASK_DEBUG: print("End of registration.")
        return status.HTTP_200_OK

    def abort(self):
        "Abort registration"
        if FLASK_DEBUG: print("End of registration - aborted.")
        send_message(str(self.user_id), "Ну и пошел нахуй тогда")
        return status.HTTP_200_OK

    def edit(self):
        #TODO: edit
        if FLASK_DEBUG: print("Updating.")
        send_message(str(self.user_id), "Not Implemented")
        return status.HTTP_501_NOT_IMPLEMENTED


class match(object):
    "Methods related to matching"

    def __init__(self, user_id, dbc, start=True):
        self.user_id = user_id
        self.dbc = dbc
        try:
            self.dbc.connect()
            user = self.dbc.get_user(self.user_id)
            self.dbc.close()
       #TODO error handlers
        except ProgrammingError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id),
                'Похоже, ты нашел ошибку у меня в коде, мой друг! ' \
                'Срочно напиши сюда (id218786773) с как можно более подробным описанием проблемы.')
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        except OperationalError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id),
                'Произошла ошибка при сохранении. Попробуй заново через какое-то время.')
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        #TODO separate sql queries from db.py
        self.city_id = user[5]
        self.goal_id = user[6]
        self.lookfor_id = user[7]
        self.gender_id = user[8]
        self.match = 0
        self.matches = []
        if start: self.start()

    def __repr__(self):
        return "uuid {0} (match {1}, all matches {2})".format(self.user_id,
            self.match, self.matches)

    def start(self):
        try:
            self.dbc.connect()
            self.matches = self.dbc.get_matches(self.user_id, self.city_id,
                self.goal_id, self.gender_id, self.lookfor_id)
            self.dbc.close()
       #TODO error handlers
        except ProgrammingError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id),
                'Похоже, ты нашел ошибку у меня в коде, мой друг! ' \
                'Срочно напиши сюда (id218786773) с как можно более подробным описанием проблемы.')
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        except OperationalError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id),
                'Произошла ошибка при сохранении. Попробуй заново через какое-то время.')
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        if self.matches:
            self.show_current_match()
        else:
            send_message(self.user_id, "Подходящей для тебя пары пока не было" \
                " найдено :( Попробуй попозже, может твоя судьба решит" \
                " зарегаться завтра!")

    def show_current_match(self):
        name, description, photo = self.matches[self.match]
        msg = "{0}\n{1}".format(name, description)
        self.send_message(user_id, msg, photo)
        self.send_message(user_id, "+/- ?")


def delete(user_id, dbc):
    try:
        dbc.connect()
        dbc.delete_user(user_id)
        dbc.close()
        send_message(user_id, "Твоя анкета была удалена.\n" \
            "Спасибо за участие и иди нахуй.")
       #TODO error handlers
    except ProgrammingError as err:
        if FLASK_DEBUG: raise(err)
        send_message(str(self.user_id),
            'Похоже, ты нашел ошибку у меня в коде, мой друг! ' \
            'Срочно напиши сюда (id218786773) с как можно более подробным описанием проблемы.')
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    except OperationalError as err:
        if FLASK_DEBUG: raise(err)
        send_message(str(self.user_id),
            'Произошла ошибка при сохранении. Попробуй заново через какое-то время.')
        return status.HTTP_500_INTERNAL_SERVER_ERROR
