import sqlite3
import json


class GameCache:
    def __init__(self, db_name=":memory:", primary_key_fields=None):
        if primary_key_fields is None:
            primary_key_fields = ["username", "month"]
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.primary_key_field_names = primary_key_fields
        self._create_table(primary_key_fields)

    def _create_table(self, primary_key_fields):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS kv_store (
                {}
                value TEXT,
                PRIMARY KEY ({})
            )
        '''.format("".join(f"{key} TEXT, " for key in primary_key_fields), ",".join(primary_key_fields)))
        self.conn.commit()

    def set(self, primary_key_field_values, value):
        value_json = json.dumps(value)
        row_data = primary_key_field_values + [value_json]
        write_query = f'''
            INSERT INTO kv_store ({",".join(self.primary_key_field_names + ["value"])})
            VALUES ({', '.join('?' for _ in row_data)})
            ON CONFLICT({",".join(self.primary_key_field_names)}) DO UPDATE SET value=excluded.value
        '''
        self.cursor.execute(write_query , [value for value in row_data])
        self.conn.commit()

    def get(self, username, day):
        self.cursor.execute('''
            SELECT value FROM kv_store WHERE username=? AND day=?
        ''', (username, day))
        rows = self.cursor.fetchall()
        return rows
        # if rows:
        #     return json.loads(row[0])
        # return None

    def delete(self, username, day):
        self.cursor.execute('''
            DELETE FROM kv_store WHERE username=? AND day=?
        ''', (username, day))
        self.conn.commit()

    def close(self):
        self.conn.close()
