# -*- coding: utf-8 -*-
from os.path import dirname, abspath
import xlwt
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from doraemon import db

app = Flask(__name__)
config_path = dirname(dirname(dirname(dirname(abspath(__file__))))) + "/config.py"
app.config.from_pyfile(config_path)
dbs = SQLAlchemy(app)
db_session = dbs.session()
workbook = xlwt.Workbook(encoding = 'utf-8')
worksheet = workbook.add_sheet('对比结果')
worksheet.write(0,1,label="URI")
worksheet.write(0,2,label="diff")
worksheet.write(0,3,label="primary")
worksheet.write(0,4,label="candidate")

task_id = [865,866,867,868]
total = 1

for task in task_id:
    uri = db_session.execute("select uri from api where id in  (select api_id from task_api where task_id=%d)" % task)
    api_uri = ""
    for y in uri:
        api_uri = str(y[0])
        break
    diff_list = db_session.execute(
        "select diffs from result where result.task_id=%d and passed = 0 GROUP BY diffs" % task)
    ab = []
    for diff in diff_list:
        result_list = db_session.execute(
            "select primary_result,candidate_result from result where result.task_id=%d and passed = 0 and diffs = '%s' limit 5" % (
            task, diff[0]))
        for result in result_list:
            worksheet.write(total,1,label = api_uri )
            worksheet.write(total,2,label = diff[0] )
            worksheet.write(total,3,label = result[0] )
            worksheet.write(total,4,label = result[1] )
            total = total + 1


workbook.save("./result.xls")