import time
import pika
import json
import random
import string


def rabbit_channel():
    credentials = pika.PlainCredentials('k12', '97S}mLrjun')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='10.202.80.196', port=5672, virtual_host='K12', credentials=credentials))
    channel = connection.channel()
    message = {
        "arg_id": 10004,
        "uri": "/1/popshuangshi/class/schedule",
        "args": "schoolId=25&classCode=PE2022031&isTest=&accessToken=ef4e3a2b-ae21-4cad-ada8-86ec46a8a83g&appId=90129",
        "primary": "https://ppssj.xdf.cn",
        "secondary": "https://ppssj.xdf.cn",
        "candidate": "https://wxbackend.xdf.cn"
    }
    body = json.dumps(message)
    channel.basic_publish(exchange='', routing_key='k12qa.doraemon.difftask', body=body)


rabbit_channel()
