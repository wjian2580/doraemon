import json
import time

from flask import jsonify
from sqlalchemy import func
from doraemon import db, pika, app
from doraemon.models import Task, Api, Args


def task_process(task, limit, god=False):
    task_apis = task.apis
    if not task_apis:
        return 'no api to run'
    channel = pika.channel()
    for api in task_apis:
        project = api.project
        primary = project.primary
        secondary = project.secondary
        candidate = project.candidate
        task_args = args_filter(api, limit=limit)
        uri = api.uri
        for arg in task_args:
            message = {
                'task_id': task.id,
                'api_id': api.id,
                'uri': uri,
                'args': arg.args,
                'primary': primary,
                'secondary': secondary,
                'candidate': candidate
            }
            body = json.dumps(message)
            try:
                if not god:
                    channel.basic_publish(exchange='doraemon', routing_key='k12qa.doraemon.difftask', body=body)
                    app.logger.info("Send Normal Message")
                else:
                    channel.basic_publish(exchange='doraemon', routing_key='k12qa.doraemon.difftask', body=body)
                    app.logger.info("Send God Message")
            except Exception as e:
                app.logger.error("Send To MQ Failed, Exception : %s", e.args)
                pika.return_broken_channel(channel)
                continue

        db.session.add(task)
        db.session.commit()
    pika.return_channel(channel)


def args_filter(api, limit, filters=1):
    args = Args.query.filter(Args.api_id == api.id).order_by(func.rand()).limit(limit)
    return args

# class Channel:
#     def __init__(self):
#         self.pika = pika
#         self.channel = self.pika.channel()
#
#     def __enter__(self):
#         pass
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.pika.return_channel(self.channel)
#
#     def send(self, message):
#         body = json.dumps(message)
#         self.channel.basic_publish(exchange='', routing_key='k12qa.doraemon.difftask', body=body)
