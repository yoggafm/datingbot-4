import os
import vk
from flask import Flask, request, json
from flask_api import FlaskAPI, status
import vkapi
import db
import settings
from settings import FLASK_DEBUG, TOKEN, PORT

# create app
app = FlaskAPI(__name__)
# ongoing registration counter
onreg = {}
# DB connecctor
dbc = db.DbConnector()

if FLASK_DEBUG:
    from pprint import pprint
    pprint(db.qna)
    for var in [v for v in vars(settings) if v.isupper()]:
        print("{0}: {1}\n".format(var, getattr(settings, var)))

@app.route('/', methods=['POST'])
def processing():
    data = request.get_json()
    if 'type' not in data.keys():
        return 'not vk'
    if data['type'] == 'confirmation':
        return settings.CONFIRM_TOKEN
    if data['type'] == 'message_new':
        if 'object' in data and 'user_id' in data['object'] and \
                                'body' in data['object']:
            user_id = data['object']['user_id']
            body = data['object']['body'].strip()
        else:
            return 'Bad request', status.HTTP_400_BAD_REQUEST

        if user_id in onreg:
            if FLASK_DEBUG:
                print("Onreg:")
                print("---")
                for uid in onreg:
                    pprint(onreg[uid])
                print("---")
                print("DB cache:")
                pprint(dbc.cache)
                print("Current step:")
                pprint(db.qna[onreg[user_id].step])
            user = onreg[user_id]
            answer = user.validate_answer(body)
            if answer is status.HTTP_404_NOT_FOUND:
                return 'Not Found', answer

            if  user.step < len(db.qna)-1:
                user.process_answer(answer)
            else:
                resp = user.process_last_answer(answer)
                if resp is status.HTTP_200_OK:
                    del user
                else:
                    return 'Server Error', resp  # error
        else:
            if '/dating' in body:
                # init registration for this user
                onreg[user_id] = vkapi.registration(user_id, dbc)
                if FLASK_DEBUG:
                    print("Adding object to onreg:")
                    pprint(onreg[user_id])
                    print("DB cache:")
                    pprint(dbc.cache)

        return 'ok'

#TODO: move error handlers to errors.py
@app.errorhandler(500)
def server_error_handler(error):
    vkapi.send_message(str(user_id), TOKEN, \
        "Проблемесы на сервере. Сорян :( Попробуй "\
        "еще раз, а если не поможет, дай знать "\
        "администрации или https://vk.com/id218786773.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', PORT))
    app.run(host='0.0.0.0', port=port)
