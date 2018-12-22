import os
import vk
import json
from flask import Flask, request, json
from flask_api import FlaskAPI, status
import vkapi
from settings import * 


app = FlaskAPI(__name__)
with open(QNA_FILE, 'r') as f:
	qna = json.loads(f.read())
# ongoing registration
onreg = {}

if FLASK_DEBUG:
	from pprint import pprint
	pprint(qna)
	print("FLASK_DEBUG: {0}\nTOKEN: {1}\n".format(FLASK_DEBUG, TOKEN))

@app.route('/', methods=['POST'])
def processing():
	data = request.get_json()
	if 'type' not in data.keys():
		return 'not vk'
	if data['type'] == 'confirmation':
		return CONFIRM_TOKEN
	if data['type'] == 'message_new':
		if 'object' in data and 'user_id' in data['object'] and \
								'body' in data['object']:
			user_id = data['object']['user_id']
			body = data['object']['body'].strip().lower()
		else:
			return 'Bad request', status.HTTP_400_BAD_REQUEST

		if user_id in onreg:
			if FLASK_DEBUG:
				print(onreg)
				pprint(qna[onreg[user_id]])
			# Process answer
			options = qna[onreg[user_id]]['a']
			answer = method_name = ''
			if not options or body in options:
				answer = body
				method_name = qna[onreg[user_id]]['f']
			elif options:  # autocomplete, only when options available
				for opt in options:
					if opt.startswith(body) or opt[3:] == body:
						answer = opt
						method_name = qna[onreg[user_id]]['f']
						break
			if options and not answer:
				vkapi.send_message(str(user_id), TOKEN,\
					'Выбери, пожалуйста, из представленных '\
					'вариантов:{}\nМожешь просто скопипастить'\
					' желаемый вариант и отправить, либо '\
					'только его начало.\nПример: для выборa '\
					'варианта "1) Брно" можно отправить: '
					'"1) Брно", "Брно", или "1", "1)", "1) Б" и т.д)'.format(
						'\n'.join(options)))
				return 'Not Found', status.HTTP_404_NOT_FOUND
			# TODO: Talk to database
			#method = getattr(qna, method_name)
			#result = method(answer)
			if FLASK_DEBUG:
				msg = "You chose variant \"{0}\", calling {1}".format(answer, method_name)
				print(msg)
			if  onreg[user_id] < len(qna)-1:
				# Ask next question
				onreg[user_id] += 1
				question = qna[onreg[user_id]]['q']
				options = qna[onreg[user_id]]['a']
				if type(options) == list:
					options = '\n'.join(options)
				elif not options:
					options = ''
				if FLASK_DEBUG: print('{0}\n{1}\n{2}'.format(onreg, question, options))
				vkapi.send_message(str(user_id), TOKEN,
									   '{0}\n{1}'.format(question, options))
			else:
				# That was last question
				onreg.pop(user_id)
				if FLASK_DEBUG: print("End of registration.")
		else:
			if '/dating' in body:
				onreg[user_id] = 0
				question = qna[0]['q']
				options = '\n'.join(qna[0]['a'])
				if FLASK_DEBUG:
					print(onreg)
					print('{0}\n{1}'.format(question, options))
				vkapi.send_message(str(user_id), TOKEN,
								   '{0}\n{1}'.format(question, options))

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
