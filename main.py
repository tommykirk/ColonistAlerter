# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import json
import logging
import os
import sys
from datetime import datetime, timedelta

import boto3
import requests
import yaml


class ColonistTracker:
    colonist_history_url = 'https://colonist.io/api/profile/{}/history'
    email_body = """
    Hi {},
    You last started a game of colonist {} minutes ago at {}. 
    In the last {} hours, you have played {} total games summing to {} of game time.
    
    Here is a helpful email to remind you that you could be doing other things
    that would make you feel better. Like nothing! Going for a walk around the block
    can provide you with the clarity you need to focus on a more rewarding activity.
    """

    def __init__(self, aws_session, max_recent_game_age_minutes, rolling_period_hours):
        self.ses = aws_session.client('ses')
        self.logger = logging.getLogger()
        self.pii = {'names': [], 'emails': []}
        self.max_recent_game_age_minutes = max_recent_game_age_minutes
        self.rolling_period_hours = rolling_period_hours
        with open('colonist-pii.yml', 'r') as stream:
            try:
                self.pii = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.logger.error(exc)

    def send_email(self, content, to_user):
        if DRY_RUN:
            print(content)
        else:
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
                        'Data': 'Helpful Reminder For {} Regarding Colonist'.format(to_user),
                    },
                },
                Source=self.pii['emails'][0],
            )

    def poll_colonist_games(self, username):
        url = ColonistTracker.colonist_history_url.format(username)
        response = requests.get(url)

        if response.status_code == 200:
            return response
        else:
            raise Exception

    def calculate_and_send_email(self, response, username, name):
        # Extract the content of the response
        last_game = response.json()['gameDatas'][-1]
        last_game_start_time = datetime.fromtimestamp(int(last_game['startTime']) // 1000)
        last_game_end_time = last_game_start_time + timedelta(milliseconds=int(last_game['duration']))
        now = datetime.now()
        last_checked_time = now - timedelta(minutes=self.max_recent_game_age_minutes)
        self.logger.info("{} last game start time: {} \n last game end time: {} \n now: {}".format(username,
                                                                                                   last_game_start_time,
                                                                                                   last_game_end_time,
                                                                                                   now))
        # Send an email with the content of the response
        if last_game_end_time < last_checked_time:
            self.logger.info('Email not sent.')
            return
        game_history_list = response.json()['gameDatas']
        duration_list = [int(game['duration']) for game in game_history_list if
                         now - datetime.fromtimestamp(int(game['startTime']) // 1000) <
                         timedelta(hours=self.rolling_period_hours)]
        games_played = len(duration_list)
        minutes_played = sum(duration_list) // 1000 // 60
        duration_played = "{} minutes".format(minutes_played) \
            if minutes_played < 60 else "{} hours".format(round(minutes_played / 60, 2))
        message = ColonistTracker.email_body.format(username,
                                                    (now - last_game_start_time).seconds // 60,
                                                    last_game_start_time,
                                                    self.rolling_period_hours,
                                                    games_played,
                                                    duration_played)

        try:
            self.send_email(message, name)
            if not DRY_RUN:
                self.logger.info('Email sent!')
        except Exception as e:
            self.logger.error(e)

    def run(self):
        for name_to_usernames_map in self.pii['usernames']:
            for name, usernames in name_to_usernames_map.items():
                for username in usernames:
                    response = self.poll_colonist_games(username)
                    self.calculate_and_send_email(response, username, name)


def main(session, max_recent_game_age_minutes, rolling_period_hours):
    # AWS SES client
    tracker = ColonistTracker(session, max_recent_game_age_minutes, rolling_period_hours)
    tracker.run()

DRY_RUN = True

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    max_recent_game_age_minutes = 60
    rolling_lookback_period_hours = 12
    main(
        boto3.Session(region_name='us-east-1'),
        max_recent_game_age_minutes,
        rolling_lookback_period_hours
    )


def lambda_handler(event, context):
    logging.getLogger().setLevel(logging.INFO)
    session = boto3.Session(region_name='us-east-1')
    max_recent_game_age_minutes = int(os.environ['COLONIST_RECENT_GAME_AGE'])
    rolling_period_hours = int(os.environ['COLONIST_ROLLING_PERIOD'])
    main(session, max_recent_game_age_minutes, rolling_period_hours)
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Colonist lambda ran successfully!')
    }
