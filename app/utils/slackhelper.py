from slackclient import SlackClient
from config import get_env
import requests

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

	def send_pdf(self, filepath, filename, channel=None, title=None, ):
		if channel is None:
			channel = self.slack_channel 
		return self.slack_client.api_call(
			'files.upload',
			filename=filename,
			channels=channel,
			file=open(filepath,'rb'),
			initial_comment='{} subject'.format(filename),
			title=title
		)

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

	def user_info(self, uid):
		return self.slack_client.api_call(
			"users.info",
			user=uid,
			token=self.slack_token
		)