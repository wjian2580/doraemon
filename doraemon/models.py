import requests

from doraemon import db, cache
from datetime import datetime


class Project(db.Model):
    __tablename__ = 'project'

    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(200), unique=True)
    primary = db.Column(db.String(50))
    secondary = db.Column(db.String(50))
    candidate = db.Column(db.String(50))
    create_time = db.Column(db.DateTime, default=datetime.now)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    apis = db.relationship('Api', backref='project')

    def __repr__(self):
        return '<Project %s>' % self.project_name


class Api(db.Model):
    __tablename__ = 'api'

    id = db.Column(db.Integer, primary_key=True)
    api_name = db.Column(db.String(200))
    uri = db.Column(db.String(200), unique=True)
    method = db.Column(db.String(50))
    noises = db.Column(db.Text)
    order_by = db.Column(db.String(500))
    create_time = db.Column(db.DateTime, default=datetime.now)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    args = db.relationship('Args', backref='api')

    def __repr__(self):
        return '<Api %s>' % self.api_name


class Args(db.Model):
    __tablename__ = 'args'

    id = db.Column(db.Integer, primary_key=True)
    args = db.Column(db.Text)
    api_id = db.Column(db.Integer, db.ForeignKey('api.id'))
    create_time = db.Column(db.DateTime, default=datetime.now)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    online_date = db.Column(db.VARCHAR, default="2020-01-01")

    @property
    def url(self):
        return self.api.uri + '?' + self.args


class Task(db.Model):
    __tablename__ = 'task'

    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(50))
    task_filter = db.Column(db.Integer, default=1)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    create_time = db.Column(db.DateTime, default=datetime.now)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    apis = db.relationship('Api', secondary='task_api', backref='task')
    results = db.relationship('Result', backref='task', cascade='all, delete-orphan')

    @property
    def failed_cases(self):
        failed_cases = [result for result in self.results if result.passed == 0]
        return failed_cases

    def __repr__(self):
        return '<Task %s>' % self.task_name


task_api = db.Table('task_api',
                    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
                    db.Column('api_id', db.Integer, db.ForeignKey('api.id'), primary_key=True)
                    )


class Result(db.Model):
    __tablename__ = 'result'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'))
    primary = db.Column(db.Text)
    candidate = db.Column(db.Text)
    primary_result = db.Column(db.Text(429400000))
    candidate_result = db.Column(db.Text(429400000))
    passed = db.Column(db.Boolean)
    diffs = db.Column(db.Text)
    primary_res_time = db.Column(db.Float)
    candidate_res_time = db.Column(db.Float)
    create_time = db.Column(db.DateTime, default=datetime.now)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
