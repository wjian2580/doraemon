DEBUG = True
SECRET_KEY = 'k12qa'
SQLALCHEMY_DATABASE_URI = 'mysql://root:k12qa123@172.24.30.42:3309/doraemon?charset=utf8mb4&autocommit=true'
SQLALCHEMY_TRACK_MODIFICATIONS = True
FLASK_REDIS_PARAMS = {
    'host': '172.24.30.42',
    'port': 39001,
    'password': '',
    'db': 0
}

CACHE_TYPE = 'redis'
CACHE_DEFAULT_TIMEOUT = 3000
CACHE_REDIS_HOST = '172.24.30.42'
CACHE_REDIS_PORT = 39001
CACHE_REDIS_DB = 0

FLASK_PIKA_PARAMS = {
    'host': '10.202.80.196',
    'username': 'k12',
    'password': '97S}mLrjun',
    'port': 5672,
    'virtual_host': 'K12',
    'socket_timeout': 5
}
# optional pooling params
FLASK_PIKA_POOL_PARAMS = {
    'pool_size': 10,
    'pool_recycle': 90
}
