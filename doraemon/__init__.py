from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_pika import Pika
from flask_cache import Cache
import logging
import redis
from config import FLASK_REDIS_PARAMS

app = Flask(__name__)
app.config.from_pyfile('../config.py')
db = SQLAlchemy(app)
pika = Pika(app)
cache = Cache(app)
redis_store = redis.Redis(FLASK_REDIS_PARAMS.get("host"), FLASK_REDIS_PARAMS.get("port"),decode_responses=True)


def register_logging(app):
    formatter = logging.Formatter(
        '[%(asctime)s] - [%(levelname)s] - [%(filename)s] - [%(funcName)s] - [%(lineno)s] - [%(message)s]')

    info_handler = logging.FileHandler("info.log")
    info_handler.setFormatter(formatter)
    info_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(info_handler)

    error_handler = logging.FileHandler("error.log")
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.WARNING)
    app.logger.addHandler(error_handler)


register_logging(app)
from doraemon import views
