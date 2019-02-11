import requests
import random
import re
import string
import os
import json
from flask_api import status
from sqlite3 import IntegrityError, OperationalError, ProgrammingError
import vk
from db import qna
from settings import *
if FLASK_DEBUG: from pprint import pprint

session = vk.Session()
api = vk.API(session, access_token=TOKEN, v=VK_API_VERSION)

def send_message(user_id, message="", attachment="", keyboard=None):
    if keyboard:
        api.messages.send(user_id=str(user_id), message=message,
            attachment=attachment, keyboard=json.dumps(keyboard, ensure_ascii=False))
    else:
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
        keyboard = {
            "one_time":False,
            "buttons":[
                [{"action":{
                    "type":"text",
                    "payload": "{\"button\": \"0\"}",
                    "label": "Закончить"
                    },
                 "color":"default"
                 }]]
        }
        if type(options) == list:
            msg = '{0}\n{1}\n{2}\n{3}'.format(prefix, question,
                '\n'.join(options), postfix)
            for i in range(len(options)):
                num = i+1
                keyboard['buttons'][0].append(
                    {"action":{
                        "type":"text",
                        "payload": "{\"button\": \"" + str(num) + "\"}",
                        "label": str(num)
                        },
                     "color":"default"
                    })
        elif not options:
            msg = '{0}\n{1}\n{2}'.format(prefix, question, postfix)
        if FLASK_DEBUG: print(msg, keyboard)
        send_message(str(self.user_id), msg, attachment, keyboard)

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
                return ''
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
        if answer == '':
            if options:
                msg = 'Выбери, пожалуйста, из представленных '\
                    'вариантов:{}\nМожешь просто скопипастить'\
                    ' желаемый вариант и отправить, либо '\
                    'только его начало.\nПример: для выборa '\
                    'варианта "1) Брно" можно отправить: '\
                    '"1) Брно", "Брно", или "1", "1)", "1) Б" '\
                    'и т.д) '.format('\n'.join(options))
            else:
                msg = 'Твой ответ не подходит, ты точно это имел '\
                    'в виду то, что написал? Попробуй еще раз.'
            send_message(str(self.user_id), msg)
            if FLASK_DEBUG: print("Illigitimate answer {}".format(body))
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
            send_message(str(self.user_id), 'Твоя анкета уже есть в базе данных!')
            # do not return error
        else:
            send_message(str(self.user_id), 'Спасибо за регистрацию! Воспользуйся командой "Поиск", чтобы просмотреть людей, которых я для тебя подберу.')
            
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
        self.city_id = None
        self.goal_id = None
        self.lookfor_id = None
        self.gender_id = None
        self.match = 0
        self.matches = []

        try:
            self.dbc.connect()
            user = self.dbc.get_user(self.user_id)
            self.dbc.close()
            if user is None:
                send_message(str(self.user_id), 'Ты еще не зарегестрирован!')
                #raise ValueError
       #TODO error handlers
        except ProgrammingError as err:
            send_message(str(self.user_id),
                'Похоже, ты нашел ошибку у меня в коде, мой друг! ' \
                'Срочно напиши сюда (id218786773) с как можно более подробным описанием проблемы.',
                keyboard={"one_time":True,"buttons":[]})
            #raise err
        except OperationalError as err:
            send_message(str(self.user_id),
                'Произошла ошибка при сохранении. Попробуй заново через какое-то время.',
                keyboard={"one_time":True,"buttons":[]})
        else:
            #TODO separate sql queries from db.py
            self.dbc.connect()
            self.city_id = self.dbc.get_city(user_id)
            self.goal_id = self.dbc.get_goal(user_id)
            self.lookfor_id = self.dbc.get_lookfor(user_id)
            self.gender_id = self.dbc.get_gender(user_id)
            self.dbc.close()
            if start: self.start()

    def __repr__(self):
        return "uuid {0} (match {1} {2}, all matches {3})".format(self.user_id,
            self.match, self.matches[self.match][1], self.matches)

    def start(self):
        try:
            self.dbc.connect()
            if self.city_id and self.goal_id and self.gender_id and self.lookfor_id:
                self.matches = self.dbc.get_matches(self.user_id, self.city_id,
                                                    self.goal_id, self.gender_id, self.lookfor_id)
            else:
                self.matches = None
                send_message(self.user_id, "Подходящей для тебя пары пока не было" \
                    " найдено :( Попробуй попозже, может твоя судьба решит" \
                    " зарегаться завтра!",
                keyboard={"one_time":True,"buttons":[]})
            self.dbc.close()
       #TODO error handlers
        except ProgrammingError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id),
                'Похоже, ты нашел ошибку у меня в коде, мой друг! ' \
                'Срочно напиши сюда (id218786773) с как можно более подробным описанием проблемы.',
                keyboard={"one_time":True,"buttons":[]})
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        except OperationalError as err:
            if FLASK_DEBUG: raise(err)
            send_message(str(self.user_id),
                'Произошла ошибка при сохранении. Попробуй заново через какое-то время.',
                keyboard={"one_time":True,"buttons":[]})
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        if self.matches:
            self.show_current_match()
        else:
            send_message(self.user_id, "Подходящей для тебя пары пока не было" \
                " найдено :( Попробуй попозже, может твоя судьба решит" \
                " зарегаться завтра!",
                keyboard={"one_time":True,"buttons":[]})

    def next(self):
        self.match += 1
        if len(self.matches) > self.match:
            self.show_current_match()
            return 1
        else:
            msg = "Подходящей для тебя пары пока не было" \
                  " найдено :( Попробуй попозже, может твоя судьба решит" \
                  " зарегаться завтра!"
            send_message(self.user_id, msg, keyboard={"one_time":True,"buttons":[]})
            return 0

    def show_current_match(self):
        _, name, description, photo = self.matches[self.match]
        msg = "{0}\n{1}".format(name, description)
        send_message(self.user_id, msg, photo)
        keyboard = {
            "one_time":False,
            "buttons": [
              [{
                "action": {
                  "type": "text",
                  "payload": "{\"button\": \"1\"}",
                  "label": "+"
                },
                "color": "default"
              },
             {
                "action": {
                  "type": "text",
                  "payload": "{\"button\": \"2\"}",
                  "label": "-"
                },
                "color": "default"
              }]
            ]
        }
        send_message(self.user_id, "+/- ?", keyboard=keyboard)


def delete(user_id, dbc):
    try:
        # check if user exists
        dbc.connect()
        user = dbc.get_user(user_id)
        dbc.close()
        if user is None:
            send_message(str(user_id), 'Ты еще не зарегестрирован!')
            return status.HTTP_404_NOT_FOUND
        dbc.connect()
        dbc.delete_user(user_id)
        dbc.close()
        send_message(user_id, "Твоя анкета была удалена.\n" \
            "Спасибо за участие и иди нахуй.",
            keyboard={"one_time":True,"buttons":[]})
        return status.HTTP_200_OK
       #TODO error handlers
    except ProgrammingError as err:
        if FLASK_DEBUG: raise(err)
        send_message(str(user_id),
            'Похоже, ты нашел ошибку у меня в коде, мой друг! ' \
            'Срочно напиши сюда (id218786773) с как можно более подробным описанием проблемы.',
            keyboard={"one_time":True,"buttons":[]})
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    except OperationalError as err:
        if FLASK_DEBUG: raise(err)
        send_message(str(user_id),
            'Произошла ошибка при сохранении. Попробуй заново через какое-то время.',
            keyboard={"one_time":True,"buttons":[]})
        return status.HTTP_500_INTERNAL_SERVER_ERROR
