import vkapi
import json
from settings import QNA_FILE

def main(user_id, token):
	qna = json.loads(QNA_FILE)  #FIXME error handling
	for q in qna:
		# Ask question
		header = q + '\n' 
		body = ''
		for num, option in enumerate(qna[q].keys()):
			body += '{0}) {1}\n'.format(num. option)
		message = header + body
		vkapi.send_message(user_id, token, message)

		# Recieve answer
		qna[q]
	
