# -*- coding: utf-8 -*-
import sys
from os.path import dirname, abspath

sys.path.append(dirname(dirname(dirname(dirname(abspath(__file__))))))
import csv
import time
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from doraemon.models import Api, Args, Project
from doraemon import db
from doraemon import redis_store
from doraemon.common.redisUtils.CONSTANT import CONSTANT
import pathos.multiprocessing as multiprocessing


def get_project_from_cache(project_name):
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


def get_api_info_from_cache(api_name, api_uri, project_id):
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


def remove_keys():
    all_key = redis_store.keys(CONSTANT.PROJECT_ID_PREFIX + "*")
    for key in all_key:
        print(key)
        redis_store.delete(key)


class kibanaAccessLogImpl:
    # 文件路径
    file_name = None
    # reader形式
    file_object = None
    # cpu核数
    cores = 2
    # 当前处理行数，最终为最大行数uri
    currentCount = 0
    # 文件流
    __file_stream__ = None
    # 文件header
    __file_header__ = None

    def __init__(self, file_name):
        self.file_name = file_name
        self.__file_stream__ = open(self.file_name, "r", encoding='utf-8')
        self.file_object = csv.reader(self.__file_stream__)
        self.cores = multiprocessing.cpu_count()

    def __get_line__(self):
        return next(self.file_object)

    def __get_lines__(self):
        temp = []
        for i in range(50):
            try:
                temp.append(next(self.file_object))
            except Exception:
                break
        return temp

    @staticmethod
    def somethingwrong(message):
        print("【子进程失败回调】  %s" % message)

    @staticmethod
    def get_uri_key(project_name, uri_string):
        return CONSTANT.PROJECT_URI_PREFIX + str(project_name) + "_" + str(uri_string)

    # 核心分析模块
    @staticmethod
    def __analyze__(each_lines, project_name, project_date, headers):
        app = Flask(__name__)
        config_path = dirname(dirname(dirname(dirname(abspath(__file__))))) + "/config.py"
        app.config.from_pyfile(config_path)
        dbs = SQLAlchemy(app)
        db_session = dbs.session()
        bulk_insert = []
        for each_line in each_lines:
            temp = dict(zip(headers, each_line))
            try:
                if temp.get("uri") and temp.get("args"):
                    cache_key = kibanaAccessLogImpl.get_uri_key(project_name.strip(), temp.get("uri").strip())
                    project = get_project_from_cache(str(project_name).strip())
                    api_name = temp.get("uri").split("/")[-1].strip()
                    api_uri = temp.get("uri").strip()
                    exist_api = get_api_info_from_cache(api_name, api_uri, project.get("id"))
                    if exist_api:
                        # args = Args(args=temp.get("args"), api_id=exist_api.get("id"), online_date=project_date)
                        # try:
                        #     db_session.add(args)
                        #     db_session.commit()
                        # except Exception as e:
                        #     db_session.rollback()
                        bulk_insert.append(
                            {"args": temp.get("args"), "api_id": exist_api.get("id"), "online_date": project_date})
                    else:
                        redis_lock_key = "-".join(
                            [str(project.get("id")), str(api_name), str(api_uri), str(project_date)])
                        lock_result = redis_store.setnx(redis_lock_key, "lock")
                        new_id = None
                        if lock_result == 1:
                            redis_store.setex(redis_lock_key, 3, "lock")
                            api = Api(api_name=api_name, uri=api_uri, project_id=project.get("id"),
                                      method=temp.get("method") if temp.get("method") else "GET")
                            result = db_session.add(api)
                            if result:
                                new_id = result.lastrowid
                            try:
                                db_session.commit()
                            except Exception as e:
                                print("mysql", e.args)
                                db_session.rollback()
                                time.sleep(0.3)
                                # exist_api = Api.query.filter(Api.api_name == api_name,
                                #                              Api.uri == api_uri,
                                #                              Api.project_id == project.get("id")).first()
                                exist_api = get_api_info_from_cache(api_name, api_uri, project.get("id"))
                                new_id = exist_api.get("id")
                        else:
                            time.sleep(0.1)
                            exist_api = get_api_info_from_cache(api_name, api_uri, project.get("id"))

                            new_id = exist_api.get("id")
                        if new_id:
                            # args = Args(args=temp.get("args"), api_id=new_id, online_date=project_date)
                            # try:
                            #     db_session.add(args)
                            #     db_session.commit()
                            # except Exception as e:
                            #     db_session.rollback()
                            bulk_insert.append(
                                {"args": temp.get("args"), "api_id": new_id, "online_date": project_date})
                    if not redis_store.exists(cache_key):
                        redis_store.hset(cache_key, project_date, 1)
                    else:
                        redis_store.hincrby(cache_key, project_date, amount=1)
                else:
                    print("No URI/args ", temp)
            except Exception as e:
                print("最终失败了...", e.args)
        if len(bulk_insert) > 0:
            db_session.execute(
                Args.__table__.insert(),
                bulk_insert
            )
            db_session.commit()
        del db_session

    def __parse_header__(self, first_line):
        self.__file_header__ = (x for x in first_line)

    # 类卸载时，需要关闭句柄
    def __del__(self):
        self.__file_stream__.close()

    def process(self):
        #pool = multiprocessing.Pool(processes=self.cores)
        pool = multiprocessing.Pool(processes=1)
        star_time = time.time()
        each_line = self.__get_line__()
        self.__parse_header__(each_line)
        file_name_base = os.path.splitext(os.path.basename(self.file_name))[0]
        project_name = "-".join(str(file_name_base).split("-")[:1])
        project_date = "-".join(str(file_name_base).split("-")[1:4])
        file_header = [x for x in self.__file_header__]
        try:
            each_line = self.__get_lines__()
            while len(each_line) > 0:
                pool.apply_async(self.__analyze__,
                                 args=(each_line, project_name, project_date, file_header),
                                 error_callback=kibanaAccessLogImpl.somethingwrong)
                each_line = self.__get_lines__()
        except StopIteration:
            print("end")
            pool.close()
            pool.join()
        except Exception:
            pass
        finally:
            try:
                exist_keys = redis_store.keys(CONSTANT.PROJECT_URI_PREFIX + project_name.strip() + "*")
                total = 0
                for keys in exist_keys:
                    if redis_store.hget(keys, project_date):
                        total = total + int(redis_store.hget(keys, project_date))
                mysql_total = Args.query.filter(Args.online_date == project_date).count()
                print("处理完毕 , Redis 总量: %d, Mysql 总量: %d" % (total, mysql_total))
            except Exception:
                pass

        print((time.time() - star_time) / 1000)

    def sum(self):
        exist_keys = redis_store.keys(CONSTANT.PROJECT_URI_PREFIX + "usercenter".strip() + "*")
        total = 0
        for keys in exist_keys:
            total = total + int(redis_store.hget(keys, "2020-07-01"))
        mysql_total = Args.query.filter(Args.online_date == "2020-07-01").count()
        print("处理完毕 , Redis 总量: %d, Mysql 总量: %d" % (total, mysql_total))


if __name__ == '__main__':
    log_path = dirname(dirname(dirname(dirname(abspath(__file__))))) + "/kibana_logs/"
    files = os.listdir(log_path)
    for f in files:
        k = kibanaAccessLogImpl(log_path + f)
        k.process()
