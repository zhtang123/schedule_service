import os
import pymysql
import logging
import time
from functools import wraps

class Database:
    MAX_RETRIES = 5
    RETRY_DELAY = 5

    def __init__(self):
        self.host = os.getenv('DB_HOST')
        self.port = os.getenv('DB_PORT')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME')
        self.cnx = None
        logging.info(f"connect db {self.host}:{self.port} {self.user} ")
        self.connect_and_initialize()

    def retry_on_failure(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = 0
            while retries < self.MAX_RETRIES:
                try:
                    if self.cnx is None or not self.cnx.open:
                        self.connect()
                    result = func(self, *args, **kwargs)
                    logging.info(f"{func.__name__} executed successfully")
                    return result
                except (pymysql.MySQLError, pymysql.OperationalError) as error:
                    logging.error(f"Error occurred in {func.__name__}: {str(error)}")
                    if retries < self.MAX_RETRIES - 1:
                        logging.info(f"Retrying in {self.RETRY_DELAY} seconds...")
                        time.sleep(self.RETRY_DELAY)
                        retries += 1
                    else:
                        raise Exception(f"Could not execute {func.__name__} after {self.MAX_RETRIES} attempts")

        return wrapper

    def connect(self):
        self.cnx = pymysql.connect(
            host=self.host,
            port=int(self.port),
            user=self.user,
            password=self.password,
            db=self.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    @retry_on_failure
    def connect_and_initialize(self):
        self.connect()

        create_table_query = """
            CREATE TABLE IF NOT EXISTS scheduled_userop (
                userophash VARCHAR(255) PRIMARY KEY,
                status VARCHAR(255),
                time DATETIME,
                task_id VARCHAR(255)
            )
        """
        with self.cnx.cursor() as cursor:
            cursor.execute(create_table_query)

        self.cnx.commit()

        logging.info("table get or create successfully")

    @retry_on_failure
    def insert_scheduled_userop(self, userophash, status, task_id, time):
        with self.cnx.cursor() as cursor:
            cursor.execute("""
                INSERT INTO scheduled_userop (userophash, status, task_id, time)
                VALUES (%s, %s, %s, %s)
            """, (userophash, status, task_id, time))
            self.cnx.commit()

    @retry_on_failure
    def get_scheduled_userop(self, userophash):
        with self.cnx.cursor() as cursor:
            cursor.execute("SELECT * FROM scheduled_userop WHERE userophash = %s", (userophash,))
            return cursor.fetchone()

    @retry_on_failure
    def get_all_scheduled_userops(self):
        with self.cnx.cursor() as cursor:
            cursor.execute("SELECT * FROM scheduled_userop")
            return cursor.fetchall()

    @retry_on_failure
    def update_scheduled_userop_status(self, userophash, status):
        with self.cnx.cursor() as cursor:
            cursor.execute("""
                UPDATE scheduled_userop
                SET status = %s
                WHERE userophash = %s
            """, (status, userophash))
            self.cnx.commit()
