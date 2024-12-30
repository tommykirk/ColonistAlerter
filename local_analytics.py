import json
import logging
import sys
from datetime import datetime
import requests
import yaml

from game_cache import GameCache


class ColonistDownloader:
    colonist_history_url = 'https://colonist.io/api/profile/{}/history'

    def __init__(self):
        self.logger = logging.getLogger()
        self.pii = {'names': [], 'emails': []}
        with open('colonist-pii.yml', 'r') as stream:
            try:
                self.pii = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.logger.error(exc)
        self.username = self.pii['usernames'][1]['Tommy'][0]
        self.primary_key_fields=["username", "day", "game_id"]
        self.db = GameCache(db_name="colonist_history.db", primary_key_fields=self.primary_key_fields)

    def download_games(self):
        url = ColonistDownloader.colonist_history_url.format(self.username)
        response = requests.get(url)
        response.raise_for_status()
        games = response.json()['gameDatas']
        for game in games:
            game_date = format_date_from_millis(game["startTime"])
            self.db.set([self.username, game_date, game["id"]], game)

    def read_game(self):
        games = self.db.get(self.username, "2024-12-29")
        print(len(games))
        for i, game in enumerate(games):
            print(i, self.transform_game(game))

    def transform_game(self, game):
        game_json = json.loads(game[0])
        won = game_json['players'][0]['username'] == self.username
        duration = game_json['duration']
        return won, duration


def format_date_from_millis(milliseconds):
    seconds = milliseconds[:-3]
    date = datetime.fromtimestamp(int(seconds))
    return date.strftime("%Y-%m-%d")

def main():
    # AWS SES client
    tracker = ColonistDownloader()
    tracker.download_games()
    tracker.read_game()

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    main()

