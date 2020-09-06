#!/bin/bash
ps -ef|grep diff_server|grep -v grep|awk '{print $2}'|xargs kill -9
ps -ef|grep "flask run"|grep -v grep|awk '{print $2}'|xargs kill -9
nohup pipenv run python -u doraemon/diff_server.py >> diff.log 2>&1 &
#nohup pipenv run python -u doraemon/diff_server_qa.py >> diff_qa.log 2>&1 &
nohup pipenv run flask run --host 0.0.0.0 >> nohup.out 2>&1 &
