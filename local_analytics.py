import json
import logging
import sys
from collections import Counter
from datetime import datetime, timedelta
import requests
import yaml

from game_cache import GameCache


class ColonistDownloader:
    colonist_history_url = 'https://colonist.io/api/profile/{}/history'

    def __init__(self, table_name="kv_store"):
        self.logger = logging.getLogger()
        self.pii = {'names': [], 'emails': []}
        with open('colonist-pii.yml', 'r') as stream:
            try:
                self.pii = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.logger.error(exc)
        self.username = self.pii['usernames'][1]['Tommy'][0]
        self.primary_key_fields=["username", "day", "game_id", "rank", "duration", "had_resignation", "elo_type"]
        self.db = GameCache(db_name="colonist_history.db", primary_key_fields=self.primary_key_fields, table_name=table_name)

    def download_games(self):
        url = ColonistDownloader.colonist_history_url.format(self.username)
        response = requests.get(url)
        response.raise_for_status()
        games = response.json()['gameDatas']
        for game in games:
            game_date, rank, duration = self.extract_values(game)
            had_resignation = self.extract_had_resignation(game)
            elo_type = self.extract_elo_type(game)
            self.db.set([self.username, game_date, game["id"], rank, duration, had_resignation, elo_type], game)

    def read_game(self, date):
        turn_count_wins = 0
        wins = 0
        turn_count_losses = 0
        losses = 0
        rows = self.db.get_rows(self.username, date)
        games_stats = [self.extract_values(json.loads(row[-1])) for row in rows]
        for i, game in enumerate(games_stats):
            turn_count = json.loads(rows[i][-1])['turnCount']
            had_resignation = rows[i][-3] == '1'
            if not had_resignation:
                if game[1] == 1:
                    turn_count_wins += turn_count
                    wins += 1
                elif game[1] == 2:
                    turn_count_losses += turn_count
                    losses += 1
            print(f"Game {i+1} result: {'won' if game[1]==1 else 'lost'} in {game[2]} minutes")
        print(f"Spent {sum(time for _, result, time in games_stats)} minutes playing {len(rows)} games of catan today {date}.")
        turn_count_losses = turn_count_losses/losses if losses != 0 else 0
        turn_count_wins = turn_count_wins/wins if wins != 0 else 0
        print(f"{turn_count_wins} in wins and {turn_count_losses} in losses")

    def extract_values(self, game):
        rank = next(player['rank'] for player in game['players'] if player['username'] == self.username)
        duration = int(game['duration']) // 1000 / 60
        game_date = format_date_from_millis(game["startTime"])
        return game_date, rank, duration

    def extract_had_resignation(self, game):
        # print(game)
        # print(type(game['players']))
        max_player_points = max(map(lambda player: player['points'], game['players']))
        # print(max_player_points)
        return game['setting']['victoryPointsToWin'] > max_player_points

    def extract_elo_type(self, game):
        return game['setting']['eloType']

    def update_rows_in_new_table(self, field_name, extraction_method, table_name="kv_store"):
        # new_primary_key_fields = self.primary_key_fields.copy()
        # new_primary_key_fields += [field_name]
        # new_game_cache = GameCache(db_name="colonist_history.db",
        #                            primary_key_fields=new_primary_key_fields,
        #                            table_name=table_name)
        rows = self.db.get_rows(self.username)
        updated_rows = 0
        for row in rows:
            if row is None:
                continue
            else:
                game = json.loads(row[-1])
                field_value = extraction_method(game)
                new_row = list(row)
                new_row[-3] = field_value
                new_row[-1] = game
                self.db.set(new_row[:-1], new_row[-1])
                updated_rows += 1
        print(f"updated {updated_rows} rows")

    def adhoc_convert_json_str_to_json(self):
        rows = self.db.get_rows(self.username)
        for row in rows:
            if int(row[2]) <= 136268357:
                if type(row[5]) is str:
                    game_json = json.loads(row[5])
                    if type(game_json) is str:
                        game_json = json.loads(game_json)
                    if type(game_json) is not dict:
                        print("error damn")
                    self.db.set(list(row[:-1]), game_json)
            else:
                print("skipping {}".format(row[2]))

class Roll:
    def __init__(self, dice_value, roll_count, resource_blocked):
        self.dice_value = dice_value
        self.roll_count = roll_count
        self.resource_blocked = resource_blocked

    def __repr__(self):
        return f"[{self.dice_value}, {self.roll_count}, {self.resource_blocked}]"


def analyze_roll_file():
    robber_state = 0
    blocked_resource = 'D'
    resource_map = {
        'grain': 'G',
        'brick': 'B',
        'lumber': 'L',
        'ore': 'O',
        'wool': 'W',
        'desert': 'D',
    }
    sums=[]
    list_of_lists = []
    for i in range(2,13):
        list_of_lists.append([])
    with open('roll_logs.txt', 'r') as file:
        for line in file:
            if 'rolled' in line:
                # Find the numbers after "dice_" and convert them to integers
                numbers = [int(part.split("_")[1]) for part in line.split() if "dice_" in part]
                if len(numbers) == 2:  # Ensure exactly two dice rolls
                    dice_sum = sum(numbers)
                    for i in range(2,13):
                        try:
                            last_roll = max(list_of_lists[i-2], key=lambda roll: roll.roll_count if roll else 0, default=None)
                        except Exception as error:
                            print(i)
                            print(list_of_lists)
                            raise error
                        this_roll_count = 1 if last_roll is None else last_roll.roll_count + 1
                        resource_blocked = blocked_resource if dice_sum == robber_state else None
                        to_append = Roll(dice_sum, this_roll_count, resource_blocked) if i == dice_sum else None
                        # print(dice_sum)
                        # print(robber_state)
                        list_of_lists[i-2].append(to_append)
            if 'moved Robber' in line:
                tile_number, resource_name = parse_robber_line(line)
                robber_state = int(tile_number)
                blocked_resource = resource_map[resource_name]
    for i, roll_list in enumerate(list_of_lists):
        extra_space = ' ' if i < 8 else ''
        print(f"{i+2}{extra_space}: {''.join([roll.resource_blocked if roll and roll.resource_blocked else str(roll.roll_count) if roll else ' ' for roll in roll_list])}")

def parse_robber_line(robber_line: str):
    words = robber_line.split()
    tile_number = words[-3].split("_")[1]
    resource_name = words[-2]
    return tile_number, resource_name


def format_date_from_millis(milliseconds):
    seconds = milliseconds[:-3]
    date = datetime.fromtimestamp(int(seconds))
    return date.strftime("%Y-%m-%d")

def main():
    # AWS SES client
    # analyze_roll_file()
    tracker = ColonistDownloader()
    # tracker.adhoc()
    tracker.download_games()
    # tracker.read_game(datetime.today().replace(day=29, month=12, year=2024).strftime("%Y-%m-%d"))
    today = datetime.today()
    # tracker.read_game(today.strftime("%Y-%m-%d"))
    # for i in range(10):
    #     day = today - timedelta(days=i)
    #     tracker.read_game(day.strftime("%Y-%m-%d"))
    tracker.read_game((datetime.today() - timedelta(days=0)).strftime("%Y-%m-%d"))
    # tracker.read_game(None)
    # tracker.update_rows_in_new_table("had_resignation", tracker.extract_had_resignation)

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    main()

