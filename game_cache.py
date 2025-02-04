import sqlite3
import json


class GameCache:
    def __init__(self, db_name=":memory:", primary_key_fields=None, table_name="kv_store"):
        if primary_key_fields is None:
            primary_key_fields = ["username", "month"]
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.primary_key_field_names = primary_key_fields
        self.table_name = table_name
        self._create_table(primary_key_fields)

    def _create_table(self, primary_key_fields):
        create_table = f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                {"".join(f"{key} TEXT, " for key in primary_key_fields)}
                value TEXT,
                PRIMARY KEY ({",".join(primary_key_fields)})
            )
        '''
        print(create_table)
        self.cursor.execute(create_table)
        self.conn.commit()

    def set(self, primary_key_field_values, value):
        value_json = json.dumps(value)
        row_data = primary_key_field_values + [value_json]
        write_query = f'''
            INSERT INTO {self.table_name} ({",".join(self.primary_key_field_names + ["value"])})
            VALUES ({', '.join('?' for _ in row_data)})
            ON CONFLICT({",".join(self.primary_key_field_names)}) DO UPDATE SET value=excluded.value
        '''
        # print(write_query)
        self.cursor.execute(write_query , [value for value in row_data])
        self.conn.commit()

    def get_values(self, username, day=None):
        day_filter = "AND day=?" if day is not None else ""
        params = [username, day]
        self.cursor.execute(f'''
            SELECT value FROM {self.table_name} WHERE username=? {day_filter}
        ''', [param for param in params if param is not None])
        values = self.cursor.fetchall()
        return values

    def get_row_by_id(self, game_id=0):
        self.cursor.execute(f'''
            SELECT * FROM {self.table_name} WHERE game_id=? 
        ''', [game_id])
        values = self.cursor.fetchall()
        return values

    def get_rows(self, username, day=None):
        day_filter = "AND day=?" if day is not None else ""
        params = [username, day]
        self.cursor.execute(f'''
            SELECT * FROM {self.table_name} WHERE username=? {day_filter}
        ''', [param for param in params if param is not None])
        rows = self.cursor.fetchall()
        return rows

    def delete(self, username, day):
        self.cursor.execute(f'''
            DELETE FROM {self.table_name} WHERE username=? AND day=?
        ''', (username, day))
        self.conn.commit()

    def close(self):
        self.conn.close()
