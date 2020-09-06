import csv
from doraemon import db
from doraemon.models import Api, Args


def csv_processer(file):
    with open(file) as f:
        data = csv.reader(f)
        for line in data:
            _, uri, args = line
            method = "GET"
            api_name = uri.split('/')[-1]
            api = Api.query.filter(Api.api_name == api_name).first()
            if not api:
                api = Api(api_name=api_name, uri=uri, method=method, project_id=1)
                db.session.add(api)
                db.session.commit()
            api_id = api.id
            arg = Args(args=args, api_id=api_id)
            db.session.add(arg)
            db.session.commit()
