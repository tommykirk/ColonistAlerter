import json
import logging
import sys
from collections import Counter
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
        self.primary_key_fields=["username", "day", "game_id", "rank", "duration"]
        self.db = GameCache(db_name="colonist_history.db", primary_key_fields=self.primary_key_fields)

    def download_games(self):
        url = ColonistDownloader.colonist_history_url.format(self.username)
        response = requests.get(url)
        response.raise_for_status()
        games = response.json()['gameDatas']
        for game in games:
            game_date, rank, duration = self.extract_values(game)
            self.db.set([self.username, game_date, game["id"], rank, duration], game)

    def read_game(self, date):
        games = self.db.get_values(self.username, date)
        games_stats = [self.extract_values(json.loads(game[0])) for game in games]
        for i, game in enumerate(games_stats):
            print(f"Game {i+1} result: {'won' if game[1]==1 else 'lost'} in {game[2]} minutes")
        print(f"Spent {sum(time for _, result, time in games_stats)} minutes playing catan today {date}.")

    def extract_values(self, game):
        rank = next(player['rank'] for player in game['players'] if player['username'] == self.username)
        duration = int(game['duration']) // 1000 / 60
        game_date = format_date_from_millis(game["startTime"])
        return game_date, rank, duration

    def run_schema_update(self, field_name, extraction_method):
        new_primary_key_fields = self.primary_key_fields.copy()
        new_primary_key_fields += [field_name]
        new_game_cache = GameCache(db_name="colonist_history.db",
                                   primary_key_fields=new_primary_key_fields,
                                   table_name="kv_store_new")
        rows = self.db.get_rows(self.username)
        updated_rows = 0
        for row in rows:
            if row is None:
                continue
            else:
                game = json.loads(row[-1])
                _, _, field_value = extraction_method(game)
                new_row = list(row)
                new_row.insert(-1, field_value)
                new_game_cache.set(new_row[:-1], new_row[-1])
                updated_rows += 1
        print(f"updated {updated_rows} rows")

def analyze_roll_file():
    sums=[]
    list_of_lists = []
    for i in range(2,13):
        list_of_lists.append([])
    with open('roll_logs3.txt', 'r') as file:
        for line in file:
        # Find the numbers after "dice_" and convert them to integers
            numbers = [int(part.split("_")[1]) for part in line.split() if "dice_" in part]
            # Add the numbers together and append the sum to the list
            if len(numbers) == 2:  # Ensure exactly two dice rolls
                dice_sum = sum(numbers)
                for i in range(2,13):
                    to_append = max(list_of_lists[i-2] + [0])+1 if i == dice_sum else 0
                    list_of_lists[i-2].append(to_append)
    for i, num_list in enumerate(list_of_lists):
        extra_space = ' ' if i < 8 else ''
        print(f"{i+2}{extra_space}: {''.join([str(num) if num != 0 else ' ' for num in num_list])}")

def format_date_from_millis(milliseconds):
    seconds = milliseconds[:-3]
    date = datetime.fromtimestamp(int(seconds))
    return date.strftime("%Y-%m-%d")

def main():
    # AWS SES client
    # analyze_roll_file()
    tracker = ColonistDownloader()
    tracker.download_games()
    tracker.read_game(datetime.today().strftime("%Y-%m-%d"))
    # tracker.run_schema_update("duration", tracker.extract_values)

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    main()

