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
        self.primary_key_fields=["username", "day", "game_id", "rank"]
        self.db = GameCache(db_name="colonist_history.db", primary_key_fields=self.primary_key_fields)

    def download_games(self):
        url = ColonistDownloader.colonist_history_url.format(self.username)
        response = requests.get(url)
        response.raise_for_status()
        games = response.json()['gameDatas']
        for game in games:
            game_date, rank, _ = self.extract_values(game)
            self.db.set([self.username, game_date, game["id"], rank], game)

    def read_game(self, date):
        games = self.db.get_values(self.username, date)
        games_stats = [self.extract_values(json.loads(game[0])) for game in games]
        for i, game in enumerate(games_stats):
            print(f"Game {i+1} result: {'won' if game[1]==1 else 'lost'} in {game[2]} minutes")
        print(f"Spent {sum(time for _, result, time in games_stats)} minutes playing catan today.")

    def extract_values(self, game):
        rank = next(player['rank'] for player in game['players'] if player['username'] == self.username)
        duration = int(game['duration']) // 1000 / 60
        game_date = format_date_from_millis(game["startTime"])
        return game_date, rank, duration

    def run_schema_update(self):
        rows = self.db.get_rows(self.username)
        updated_rows = 0
        for row in rows:
            if row[3] is not None:
                continue
            else:
                game = json.loads(row[4])
                game_date, rank, _ = self.extract_values(game)
                self.db.set([self.username, game_date, game["id"], rank], game)
                updated_rows += 1
        print(f"updated {updated_rows} rows")



def format_date_from_millis(milliseconds):
    seconds = milliseconds[:-3]
    date = datetime.fromtimestamp(int(seconds))
    return date.strftime("%Y-%m-%d")

def main():
    # AWS SES client
    tracker = ColonistDownloader()
    tracker.download_games()
    tracker.read_game(datetime.today().strftime("%Y-%m-%d"))
    # tracker.run_schema_update()

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    main()

