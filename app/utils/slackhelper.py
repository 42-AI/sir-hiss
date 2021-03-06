from slackclient import SlackClient
from config import get_env
import requests
import threading

class SlackHelper:

	def __init__(self):
		self.slack_token = get_env('SLACK_TOKEN')
		self.slack_client = SlackClient(self.slack_token)
		self.slack_channel = get_env('SLACK_CHANNEL')

	def post_message(self, msg, recipient):
		return self.slack_client.api_call(
			"chat.postMessage",
			channel=recipient,
			text=msg,
			as_user=True
		)

	def post_message_to_channel(self, msg):
		return  self.slack_client.api_call(
			"chat.postMessage",
			channel=self.slack_channel,
			text=msg,
			username='turing',
			parse='full',
			as_user=False
		)

	def pdf_upload(self, filepath, filename, channel=None, title=None, ):
		if channel is None:
			channel = self.slack_channel
		def wrap(filename, channel, filepath, title):
			self.slack_client.api_call(
				'files.upload',
				filename=filename,
				channels=channel,
				file=open(filepath,'rb'),
				initial_comment='{} subject'.format(filename),
				title=title
			)
		t = threading.Thread(target=wrap, args=(filename, channel, filepath, title))
		t.start()

	def file_upload(self, file_content, file_name, file_type, channel=None, title=None, ):
		if channel is None:
			channel = self.slack_channel 
		return self.slack_client.api_call(
			"files.upload",
			channels=channel,
			content=file_content,
			filename=file_name,
			filetype=file_type,
			initial_comment='{} subject'.format(file_name),
			title=title
		)

	def introduce_correctors(self, user_id1, user_id2, day, msg):
		message = msg.format(day)
		open_response = self.slack_client.api_call(
			"conversations.open",
			token=self.slack_token,
			users="{},{}".format(user_id1, user_id2)
		)
		if open_response['ok'] is False:
			return open_response
		post_response = self.slack_client.api_call(
			'chat.postMessage',
			token=self.slack_token,
			channel=open_response['channel']['id'],
			text=message
		)
		return post_response
		
	def user_info(self, uid):
		return self.slack_client.api_call(
			"users.info",
			user=uid,
			token=self.slack_token
		)