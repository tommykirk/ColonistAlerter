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


def main():
    tracker = ColonistTracker()

    # API endpoint
    url = 'https://colonist.io/api/profile/{}/history'.format('Fara2147')

    # Send a GET request to the API
    response = requests.get(url)

    # Check if the response was successful
    if response.status_code == 200:
        # Extract the content of the response
        last_game_start_time = datetime.fromtimestamp(int(response.json()[-1]['startTime']) // 1000)
        now = datetime.now()
        last_checked_time = now - timedelta(minutes=60)
        tracker.logger.info("last game start time: {}".format(last_game_start_time))
        tracker.logger.info("last checked time: {}".format(last_checked_time))

        body = """
You last started a game of colonist at {}. That is {} minutes ago. 
Here is a helpful email to remind you that you could be doing other things
that would make you feel better. Like nothing! A simple walk,
or lying on your bed with your thoughts, can make you feel better than colonist.
""".format(last_game_start_time, (now - last_game_start_time).seconds // 60)
        print(body)
        # Send an email with the content of the response
        if last_game_start_time > last_checked_time:
            try:
                tracker.send_email(body)
                print('email sent')
            except Exception as e:
                tracker.logger.error(e)
            pass
        else:
            print('email not sent')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
