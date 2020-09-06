import csv
from doraemon import db
from doraemon.models import Api, Args


def csv_processer(file, api_id):
    with open(file) as f:
        data = csv.reader(f)
        for line in data:
            *_, uri, args = line
            method = "GET"
            api = Api.query.get(api_id)
            arg = Args(args=args, api_id=api.id)
            api.args.append(arg)
        db.session.commit()
