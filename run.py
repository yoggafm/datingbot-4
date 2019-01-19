import os
import json
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
# ongoing matching counter
onmatch = {}
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
    payload = body = None
    if FLASK_DEBUG:
        print("REQUEST ", end='')
        pprint(data)
    if 'type' not in data.keys():
        return 'not vk'
    if data['type'] == 'confirmation':
        return settings.CONFIRM_TOKEN
    if data['type'] == 'message_reply':
        return 'reply'
    if data['type'] == 'message_new':
        if 'object' in data and 'user_id' in data['object']:
            user_id = data['object']['user_id']
            if 'body' in data['object']:
                body = data['object']['body'].strip()
            if 'payload' in data['object']:
                # keyboard
                payload =  data['object']['payload']
                if 'start' in payload:
                    vkapi.send_message(user_id, "Привет!",
                        keyboard=settings.COMMANDS_KEYBOARD)
                    return 'ok'
            else:
                payload = None
        else:
            return 'Bad request', status.HTTP_400_BAD_REQUEST

        if user_id in onreg:
            user = onreg[user_id]
            if '/end' in body or 'Закончить' in body:
                clear_onreg(user)
                return 'ok'
            if len(body):
                answer = user.validate_answer(body=body)
            elif 'attachments' in data['object']:
                # attachment
                if 'photo' in data['object']['attachments'][0]:
                    photo = data['object']['attachments'][0]['photo']
                    answer = user.validate_answer(photo=photo)
            if answer is status.HTTP_404_NOT_FOUND:
                return 'Not Found', answer

            if  user.step < len(db.qna)-1:
                user.process_answer(answer)
                if user.step < len(db.qna)-1:
                    user.ask_current_question()
                else:
                    # before final step
                    postfix, photo = user.view()
                    user.ask_current_question(postfix=postfix,attachment=photo)
            # final step
            elif int(answer) < 2:
                # save and finish
                resp = user.commit()
                if resp is status.HTTP_200_OK:
                    clear_onreg(user)
                else:
                    return 'Server Error', resp  # error
            elif int(answer) > 2:
                # edit
                user.edit()
            else:
                # abort
                user.abort()
                clear_onreg(user)
            if FLASK_DEBUG:
                print("Onreg:")
                print("---")
                for uid in onreg:
                    pprint(onreg[uid])
                print("---")
                print("DB cache:")
                pprint(dbc.cache)
                if user_id in onreg:
                    print("Current step:")
                    pprint(db.qna[onreg[user_id].step])

        if user_id in onmatch:
            user = onmatch[user_id]
            match = user.matches[user.match]
            if '/end' in body or 'Закончить' in body:
                clear_onmatch(user)
                return 'ok'
            elif '+' in body:
                msg = "Скорее напиши {0}! Адрес страницы - vk.com/id{1}. \
                      Желаю удачи ;)".format(match[1], match[0])
                vkapi.send_message(user_id, msg,
                    keyboard={"one_time":True,"buttons":[]})
                clear_onmatch(user)
            elif '-' in body:
                user.match += 1
                if len(onmatch[user_id].matches) > onmatch[user_id].match:
                    user.show_current_match()
                else:
                    msg = "Подходящей для тебя пары пока не было" \
                        " найдено :( Попробуй попозже, может твоя судьба решит" \
                        " зарегаться завтра!"
                    vkapi.send_message(user_id, msg,
                        keyboard={"one_time":True,"buttons":[]})
                    clear_onmatch(user)
            if FLASK_DEBUG:
                print("Onmatch:")
                print("---")
                for uid in onmatch:
                    pprint(onmatch[uid])
                print("---")

        else:
            if '/reg' in body or 'Регистрация' in body:
                # init registration for this user
                user = onreg[user_id] = vkapi.registration(user_id, dbc)
                if not user:
                    clear_onreg(user)
                elif FLASK_DEBUG:
                    print("Adding object to onreg:")
                    pprint(onreg[user_id])
                    print("DB cache:")
                    pprint(dbc.cache)
            elif '/match' in body or 'Поиск' in body:
                # start matching
                user = onmatch[user_id] = vkapi.match(user_id, dbc)
                if not (user and onmatch[user_id].matches):
                    clear_onmatch(user)
                elif FLASK_DEBUG:
                    print("Adding object to onmatch:")
                    pprint(onmatch[user_id])
            elif '/delete' in body or 'Удалить свою анкету' in body:
                # remove user from db
                vkapi.delete(user_id, dbc)
            elif '/help' in body or 'Помощь' in body:
                # send help
                vkapi.send_message(user_id, '''Справка по командам:
                    /reg / Регистрация - зарегестироваться в системе знакомств Брно
                    и мемовой заговора
                    /delete / Удалить свою анкету - удалиться из системы
                    /match / Поиск - посмотреть подходящих тебе людей (мэтчей)
                    /end / Закончить - прекратить любую коммуникацию с ботом (работает
                    посреди регистрации или просмотра мэтчей)''',
                    keyboard={"one_time":True,"buttons":[]})
        return 'ok'
    return 'unknown'

def clear_onreg(user):
    vkapi.send_message(str(user.user_id), 'До новых встреч!',
        keyboard={"one_time":True,"buttons":[]})
    try:
        del dbc.cache[user.user_id]
    except KeyError as e:
        if FLASK_DEBUG: print(e)
        else: pass

    try:
        del onreg[user.user_id]
    except KeyError as e:
        if FLASK_DEBUG: print(e)
        else: pass

    try:
        del user
    except KeyError as e:
        if FLASK_DEBUG: print(e)
        else: pass

def clear_onmatch(user):
    vkapi.send_message(str(user.user_id), 'До новых встреч!',
        keyboard={"one_time":True,"buttons":[]})
    try:
        del onmatch[user.user_id]
    except KeyError as e:
        if FLASK_DEBUG: print(e)
        else: pass
    try:
        del user
    except KeyError as e:
        if FLASK_DEBUG: print(e)
        else: pass

#TODO: move error handlers to errors.py
@app.errorhandler(500)
def server_error_handler(error):
    data = request.get_json()
    if 'object' in data and 'user_id' in data['object']:
            user_id = data['object']['user_id']
    vkapi.send_message(str(user_id), TOKEN, \
        "Проблемесы на сервере. Сорян :( Попробуй "\
        "еще раз, а если не поможет, дай знать "\
        "администрации или https://vk.com/id218786773.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', PORT))
    app.run(host='0.0.0.0', port=port)
