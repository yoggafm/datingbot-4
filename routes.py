import os
import vk
from flask import Flask, request, json, Response
from flask_api import FlaskAPI, status
from settings import * 

app = FlaskAPI(__name__)

@app.route('/callback', methods=['POST'])
def callback():
	data = request.get_json()
	if 'type' in data and data['type'] == 'confirmation':
		if 'group_id' in data:
			if data['group_id'] == GROUP_ID:
				return CONFIRM_TOKEN
			else:
				return 'Bad group_id', status.HTTP_401_UNAUTHORIZED
		else:
			return 'Provide group_id', status.HTTP_401_UNAUTHORIZED
	return 'Bad request', status.HTTP_400_BAD_REQUEST 

@app.route('/new_message', methods=['POST'])
def new_message():
	data = request.get_json()
	if 'type' in data and data['type'] == 'message_new':
		session = vk.Session()
		api = vk.API(session, v=VK_API_VERSION)
		if 'object' in data and 'user_id' in data['object']:
			user_id = data['object']['user_id']
		else:
			return 'Bad request', status.HTTP_400_BAD_REQUEST
		api.messages.send(access_token=TOKEN, user_id=str(user_id), message='Sasat+lezhat')
		return 'ok'

if __name__ == '__main__':
	port = int(os.environ.get('PORT', PORT))
	app.run(host='0.0.0.0', port=port)
