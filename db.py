import sqlite3
from settings import DB_FILE, FLASK_DEBUG

class DbConnector(object):
    def __init__(self):
        self.cache = {}
        self._db = None
        self._conn = None
        self._cursor = None
        self._isconnected = False

    def connect(self, conn=None, cursor=None):
        self._db = DB_FILE
        self._conn = conn or sqlite3.connect(self._db)
        self._cursor = cursor or self._conn.cursor()
        self._isconnected = True
        if FLASK_DEBUG:
            print('DB connection opened.')
            print(self.isconnected)

    @property
    def connection(self):
        return self._conn

    @property
    def cursor(self):
        return self._cursor

    @property
    def isconnected(self):
        return self._isconnected

    def clear_user_cache(self, user_id):
        self.cache.pop(user_id)

    def clear_cache(self):
        self.cache = {}

    def copy_from_cache(self, user_id):
        for field in self.cache[user_id]:
            self.update(user_id, field, self.cache[user_id][field])
        self.clear_user_cache(user_id)

    def close(self, commit=True):
        if commit and self.isconnected:
            self.connection.commit()
        self.connection.close()
        self._isconnected = False
        if FLASK_DEBUG:
            print('DB connection closed.')
            print(self.isconnected)

    def save(self, user_id=None):
        "Copy from cache, commit and close connection."
        if user_id: self.copy_from_cache(user_id)
        self.close()

    def sqlquery(func):
        def wrapper(self, *args):
            if not self.isconnected:
                self.connect()
            func(self, *args)
            self.close()
        return wrapper
    
    @sqlquery
    def create_user(self, user_id):
        sql = "INSERT INTO users (id) VALUES ('{}')".format(user_id)
        self.cursor.execute(sql)

    @sqlquery
    def update(self, user_id, field, value):
        sql = '''UPDATE users SET {0}='{1}'
            WHERE id={2}'''.format(field, value, user_id)
        self.cursor.execute(sql)

    @sqlquery
    def set_city(self, user_id, city_id):
        sql = '''UPDATE users SET city_id={0}
            WHERE id={1}'''.format(city_id, user_id)
        self.cursor.execute(sql)

    @sqlquery
    def set_goal(self, user_id, goal_id):
        sql = '''UPDATE users SET goal_id={0}
            WHERE id={1}'''.format(goal_id, user_id)
        self.cursor.execute(sql)

    @sqlquery
    def set_lookfor(self, user_id, lookfor_id):
        sql = '''UPDATE users SET lookfor_id={0}
            WHERE id={1}'''.format(lookfor_id, user_id)
        self.cursor.execute(sql)

    @sqlquery
    def set_description(self, user_id, desc):
        sql = '''UPDATE users SET description='{0}'
            WHERE id={1}'''.format(desc, user_id)
        self.cursor.execute(sql)

    @sqlquery
    def set_photo(self, user_id, photo_url):
        sql = '''UPDATE users SET photo='{0}'
            WHERE id={1}'''.format(photo_url, user_id)
        self.cursor.execute(sql)
