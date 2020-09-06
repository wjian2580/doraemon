# -*- coding: utf-8 -*-
import sys
from os.path import dirname, abspath

sys.path.append(dirname(dirname(dirname(dirname(abspath(__file__))))))
import pandas as pd
import csv
import time
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from doraemon.models import Api, Args, Project
from doraemon import db
from doraemon import redis_store
from doraemon.common.redisUtils.CONSTANT import CONSTANT
import pathos.multiprocessing as multiprocessing
import shutil
import datetime

TO_SPLIT = 5000


app = Flask(__name__)
config_path = dirname(dirname(dirname(dirname(abspath(__file__))))) + "/config.py"
app.config.from_pyfile(config_path)
dbs = SQLAlchemy(app)
db_session = dbs.session()

def get_cached_project_info(project_name):
    key = CONSTANT.PROJECT_ID_PREFIX + "_" + str(project_name).strip()
    project_from_cache = redis_store.hgetall(key)
    if project_from_cache:
        return project_from_cache
    else:
        project = Project.query.filter(Project.project_name == str(project_name).strip()).first()
        if project:
            tmp = project.__dict__
            tmp.pop("_sa_instance_state")
            tmp.pop("create_time")
            tmp.pop("update_time")
            redis_store.hmset(name=key, mapping=tmp)
            redis_store.expire(name=key, time=3600 * 24 * 7)
            return tmp


def get_cached_api_info(api_name, api_uri, project_id):
    key = CONSTANT.API_INFO_PREFIX + "_" + str(project_id) + "_" + str(api_uri).strip()
    api_info_from_cache = redis_store.hgetall(key)
    if api_info_from_cache:
        return api_info_from_cache
    else:
        exist_api = Api.query.filter(Api.api_name == api_name,
                                     Api.uri == api_uri, Api.project_id == int(project_id)).first()
        if exist_api:
            tmp = exist_api.__dict__
            tmp.pop("_sa_instance_state")
            tmp.pop("create_time")
            tmp.pop("update_time")
            tmp.pop("order_by")
            if not tmp.get("noises"):
                tmp.pop("noises")
            redis_store.hmset(name=key, mapping=tmp)
            redis_store.expire(name=key, time=3600 * 24)
            return tmp


def get_or_save_api_info(api_name, api_uri, project_id, method="GET"):
    exist_api = get_cached_api_info(api_name, api_uri, project_id)
    if exist_api:
        return exist_api
    else:
        api = Api(api_name=api_name, uri=api_uri, project_id=project_id,
                  method=method)
        db_session.add(api)
        db_session.commit()
        db_session.close()
        return get_cached_api_info(api_name, api_uri, project_id)


def process_csv_file(fn, proname, prodate):
    total = 0
    time.sleep(10)
    a = time.time()
    project_info = get_cached_project_info(proname)
    if not project_info:
        print("Project : %s =========== 不存在 ========= " % proname)
        return
    df = pd.DataFrame(pd.read_csv(fn))
    # 先排序，再去重，取到所有uri 
    df.sort_values(by="uri")
    df.set_index("uri")
    uris = df.get("uri").drop_duplicates()
    # 遍历所有uri
    for uri in uris:
        # 获取所有uri相关数据
        uri_args = df.loc[(df["uri"] == uri)]
        api_name = uri.split("/")[-1].strip()
        api_info = get_or_save_api_info(api_name, uri, project_info.get("id"))
        if not api_info:
            print("api : %s ============插入失败============" % uri)
            continue
        else:
            all_args = uri_args["args"]
            all_count = all_args.shape[0]
            remainder = all_count % TO_SPLIT
            pre_times = int((all_count - remainder) / TO_SPLIT)
            if remainder > 0:
                pre_times = pre_times + 1
            dateTime_p = datetime.datetime.now()
            str_p = datetime.datetime.strftime(dateTime_p, '%Y-%m-%d %H:%M:%S')
            for i in range(pre_times):
                before = i * TO_SPLIT
                after = i * TO_SPLIT + TO_SPLIT - 1
                tmp = all_args.values[before:after]
                db_session.execute(
                    Args.__table__.insert(),
                    [{"args": x, "api_id": api_info.get("id"), "create_time": str_p, "update_time": str_p,
                      "online_date": prodate} for x in tmp])
                db_session.commit()
                db_session.close()
            total = total + all_count

        print("URI ===>  %s finished total ===> %s"%(uri, str(all_count)))
    print("Total : %s args inserted %s finished in %s s"%(str(total),fn,str(time.time()-a)))
    return True


if __name__ == '__main__':
    # 获取目录下文件
    log_path = dirname(dirname(dirname(dirname(abspath(__file__))))) + "/kibana_logs/"
    finish_path = dirname(dirname(dirname(dirname(abspath(__file__))))) + "/kibana_logs/finished/"
    files = os.listdir(log_path)
    for f in files:
        # 只操作 csv 文件
        if os.path.splitext(f)[-1] == ".csv":
            file_name = os.path.join(log_path, f)
            file_name_base = os.path.splitext(os.path.basename(file_name))[0]
            project_name = "-".join(str(file_name_base).split("-")[:1])
            project_date = "-".join(str(file_name_base).split("-")[1:4])
            print(file_name, file_name_base, project_name, project_date)
            process_status = process_csv_file(file_name, project_name, project_date)
            if process_status:
                shutil.move(file_name, os.path.join(finish_path, f))