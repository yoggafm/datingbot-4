from flask_api import status
from sqlite3 import IntegrityError, OperationalError, ProgrammingError
import vk
from db import qna
from settings import FLASK_DEBUG, TOKEN, VK_API_VERSION

session = vk.Session()
api = vk.API(session, v=VK_API_VERSION)

def send_message(user_id, token, message, attachment=""):
    api.messages.send(access_token=token, user_id=str(user_id), message=message,
                      attachment=attachment)

class registration(object):
    "Methods related to dating registration"

    def __init__(self, user_id, start=True):
        self.user_id = user_id
        self.step = 0
        if start: self.start()

    def __repr__(self):
        return "uuid {0} ({1} step)".format(self.user_id, self.step)

    def start(self):
        question = qna[0]['q']
        options = '\n'.join(qna[0]['a'])
        if FLASK_DEBUG: print('{0}\n{1}'.format(question, options))
        send_message(str(self.user_id), TOKEN, '{0}\n{1}'.format(question, options))

    def ask_current_question(self):
        question = qna[self.step]['q']
        options = qna[self.step]['a']
        if type(options) == list:
            options = '\n'.join(options)
        elif not options:
            options = ''
        if FLASK_DEBUG: print('{0}\n{1}\n'.format(question, options))
        send_message(str(self.user_id), TOKEN, '{0}\n{1}'.format(question, options))

    def validate_answer(self, body):
        "Validate user's answer to reistration questions"
        options = qna[self.step]['a']
        answer = col = ''
        if options:
            # options
            for opt in options:
                if opt.startswith(body) or opt[3:].startswith(body):
                    answer = int(opt[:1])
                    col = qna[self.step]['f']
                    break
        else:
            # free text/photo
            answer = body
            col = qna[self.step]['f']
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

    def process_answer(self, dbc, answer):
        "Execute actions required after question has been answered"
        # save to cache
        col = qna[self.step]['f']
        dbc.cache[self.user_id][col] = answer
        # ask next question
        self.step += 1
        self.ask_current_question()

    def process_last_answer(self, dbc, answer):
        if answer < 2:
            # save changes to db
            try:
                dbc.create_user(self.user_id)
                dbc.save(self.user_id)
            except ProgrammingError as err:
                if FLASK_DEBUG: print(err)
                send_message(str(self.user_id), TOKEN,
                    'Похоже, ты нашел ошибку у меня в коде, мой друг! ' \
                    'Срочно напиши сюда (id218786773) с как можно более подробным описанием проблемы.')
                return status.HTTP_500_INTERNAL_SERVER_ERROR
            except OperationalError as err:
                if FLASK_DEBUG: print(err)
                send_message(str(self.user_id), TOKEN,
                    'Произошла ошибка при сохранении. Попробуй заново через какое-то время.')
                return status.HTTP_500_INTERNAL_SERVER_ERROR
            except IntegrityError as err:
                if FLASK_DEBUG: print(err)
                send_message(str(self.user_id), TOKEN,
                    'Твоя анкета уже есть в базе данных!.')
                # do not return error
            if FLASK_DEBUG: print("End of registration.")
            send_message(str(self.user_id), TOKEN, 'До новых встреч!')
            return status.HTTP_200_OK

        elif answer == 2:
            # abort
            if FLASK_DEBUG: print("End of registration - aborted.")
            send_message(str(self.user_id), TOKEN, "Ну и пошел нахуй тогда")
            return status.HTTP_200_OK

        else:
            #TODO: edit
            if FLASK_DEBUG: print("Updating.")
            send_message(str(self.user_id), TOKEN, "Not Implemented")
            return status.HTTP_501_NOT_IMPLEMENTED
