import os
import pymysql
from contextlib import contextmanager
import logging

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建 MySQL 连接的上下文管理器
@contextmanager
def get_connection():
    connection = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        yield connection
    finally:
        connection.close()

# 自定义装饰器，用于记录日志和处理异常
def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        logger.info(f"Entering {func.__name__}")
        try:
            return func(*args, **kwargs)
        except pymysql.OperationalError as e:
            logger.exception(f"Database error in {func.__name__}: {str(e)}. Retrying...")
            return func(*args, **kwargs)  # Retry the function
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {str(e)}")
            raise
        finally:
            logger.info(f"Exiting {func.__name__}")
    return wrapper

# 创建调度的交易表
@handle_exceptions
def create_scheduled_userop_table():
    with get_connection() as connection, connection.cursor() as cursor:
        query = """
        CREATE TABLE IF NOT EXISTS scheduled_userop (
            userophash VARCHAR(255) PRIMARY KEY,
            status VARCHAR(255) NOT NULL,
            task_id VARCHAR(255),
        )
        """
        cursor.execute(query)
    connection.commit()

# 根据 userop 获取调度的交易信息
@handle_exceptions
def get_scheduled_userop_by_userophash(userophash: str):
    with get_connection() as connection, connection.cursor() as cursor:
        query = "SELECT * FROM scheduled_userop WHERE userophash = %s"
        cursor.execute(query, userophash)
        result = cursor.fetchone()
        if result:
            return result
        return None

# 获取所有调度的交易
@handle_exceptions
def get_all_scheduled_userops():
    with get_connection() as connection, connection.cursor() as cursor:
        query = "SELECT * FROM scheduled_userop"
        cursor.execute(query)
        results = cursor.fetchall()
        return results

# 创建调度的交易
@handle_exceptions
def create_scheduled_userop(userophash: str, status: str):
    with get_connection() as connection, connection.cursor() as cursor:
        query = "INSERT IGNORE INTO scheduled_userop (userophash, status) VALUES (%s, %s)"
        values = (userophash, status)
        cursor.execute(query, values)
    connection.commit()

# 更新调度的交易状态
@handle_exceptions
def update_scheduled_userop_status(userophash: str, status: str):
    with get_connection() as connection, connection.cursor() as cursor:
        query = "UPDATE scheduled_userop SET status = %s WHERE userophash = %s"
        values = (status, userophash)
        cursor.execute(query, values)
    connection.commit()
