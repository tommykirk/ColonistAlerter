# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import boto3
import logging
import requests
import sys
from datetime import datetime, timedelta

import yaml

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

colonist_history_url = 'https://colonist.io/api/profile/{}/history'
email_body = """
Hi {},
You last started a game of colonist at {}. That was {} minutes ago. 
Here is a helpful email to remind you that you could be doing other things
that would make you feel better. Like nothing! Going for a walk around the block
can provide you with the clarity you need to focus on a more rewarding activity.
"""


class ColonistTracker:
    def __init__(self):
        # AWS SES client
        session = boto3.Session(profile_name='my-sso-profile', region_name='us-east-1')
        self.ses = session.client('ses')
        self.logger = logging.getLogger()
        self.pii = {'usernames': [], 'emails': []}
        with open('pii.yml', 'r') as stream:
            try:
                self.pii = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.logger.error(exc)

    def send_email(self, content):
        self.ses.send_email(
            Destination={
                'ToAddresses': self.pii['emails'],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': 'UTF-8',
                        'Data': content,
                    },
                },
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': 'Helpful Reminder Regarding Colonist',
                },
            },
            Source=self.pii['emails'][0],
        )

    def poll_colonist_games(self, username):
        url = colonist_history_url.format(username)
        response = requests.get(url)

        if response.status_code == 200:
            return response
        else:
            raise Exception

    def calculate_and_send_email(self, response, username):
        # Extract the content of the response
        last_game_start_time = datetime.fromtimestamp(int(response.json()[-1]['startTime']) // 1000)
        now = datetime.now()
        last_checked_time = now - timedelta(minutes=60)
        self.logger.info("{} last game start time: {}, now: {}".format(username, last_game_start_time, now))
        message = email_body.format(username, last_game_start_time, (now - last_game_start_time).seconds // 60)
        # Send an email with the content of the response
        if last_game_start_time > last_checked_time:
            try:
                self.send_email(message)
            except Exception as e:
                self.logger.error(e)
        else:
            self.logger.info('Email not sent')

    def run(self):
        for username in self.pii['usernames']:
            response = self.poll_colonist_games(username)
            self.calculate_and_send_email(response, username)


def main():
    tracker = ColonistTracker()
    tracker.run()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
