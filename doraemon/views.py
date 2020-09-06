import datetime

from flask import request, redirect, url_for, jsonify, render_template, abort

from doraemon import app, db, cache
from doraemon.task_processer import task_process
from .forms import AddProjectForm, EditProjectForm, AddTaskForm, EditApiForm
from .models import Task, Project, Api, Args, Result
from sqlalchemy import func


@app.route('/')
@app.route('/index/')
@cache.cached(key_prefix='index', timeout=60*60*24)
def index():
    counts = get_counts()
    statistics = get_result_statistics()
    return render_template('index.html', counts=counts, **statistics)


@app.route('/project_list/')
def project_list():
    projects = Project.query.all()
    if request.is_xhr:
        return jsonify([(project.id, project.project_name) for project in projects])
    return render_template('project_list.html', projects=projects)


@app.route('/add_project/', methods=['POST', 'GET'])
def add_project():
    form = AddProjectForm()
    if form.validate_on_submit():
        project = Project(
            project_name=form.project_name.data,
            primary=form.primary.data,
            secondary=form.secondary.data,
            candidate=form.candidate.data
        )
        db.session.add(project)
        db.session.commit()
        return redirect(url_for('project_list'))
    return render_template('add_project.html', form=form)


@app.route('/task_list/')
def task_list():
    tasks = Task.query.order_by(Task.create_time.desc()).limit(20)
    # if request.iss_xhr:
    # 	return jsonify([(project.id, project.project_name) for project in projects])
    return render_template('task_list.html', tasks=tasks)


@app.route('/add_task/', methods=['POST', 'GET'])
def add_task():
    form = AddTaskForm()
    if form.validate_on_submit():
        task = Task(
            task_name=form.task_name.data,
            project=form.project.data,
            filters=form.filters.data
        )
        db.session.add(task)
        db.session.commit()
        return redirect(url_for('task_list'))
    return render_template('add_task.html', form=form)


@app.route('/api/run_task/<int:task_id>', methods=['POST', 'GET'])
def run_task(task_id):
    task = Task.query.get(task_id)
    task_process(task, limit=10)
    return jsonify({'success': 'true'}), 200


@app.route('/api/run_api/<int:api_id>', methods=['POST', 'GET'])
def run_api(api_id):
    api = Api.query.get(api_id)
    limit = 500
    project_id = api.project.id
    task_name = 'tmp_api_task' + '_' + api.api_name
    task = Task(task_name=task_name, project_id=project_id, task_filter=1)
    task.apis.append(api)
    db.session.add(task)
    db.session.commit()
    if not request.args.get("godWish", False):
        task_process(task, limit=limit)
    else:
        task_process(task, limit=request.args.get("godWish", 100), god=True)
    return jsonify({'success': 'true'}), 200


@app.route('/api/run_project/<int:project_id>', methods=['POST', 'GET'])
def run_project(project_id):
    project = Project.query.get(project_id)
    project_id = project.id
    task_name = 'tmp_project_task' + '_' + project.project_name
    task = Task(task_name=task_name, project_id=project_id, task_filter=1)
    apis = project.apis
    [task.apis.append(api) for api in apis]
    db.session.add(task)
    db.session.commit()
    task_process(task, limit=10)
    return jsonify({'success': 'true'}), 200


@app.route('/failed_list/<int:task_id>')
def failed_list(task_id):
    task = Task.query.get(task_id)
    failed_cases = task.failed_cases
    return render_template('failed_list.html', failed_cases=failed_cases)


@app.route('/edit_project/<int:project_id>', methods=['POST', 'GET'])
def edit_project(project_id):
    form = EditProjectForm()
    project = Project.query.get(project_id)
    if form.validate_on_submit():
        project.project_name = form.project_name.data
        project.primary = form.primary.data
        project.secondary = form.secondary.data
        project.candidate = form.candidate.data
        db.session.commit()
        return redirect(url_for('project_list'))
    form.project_name.data = project.project_name
    form.primary.data = project.primary
    form.secondary.data = project.secondary
    form.candidate.data = project.candidate
    return render_template('edit_project.html', form=form)


@app.route('/edit_api/<int:api_id>', methods=['POST', 'GET'])
def edit_api(api_id):
    form = EditApiForm()
    api = Api.query.get(api_id)
    if form.validate_on_submit():
        api.api_name = form.api_name.data
        api.noises = form.noises.data
        api.order_by = form.order_by.data
        db.session.commit()
        return redirect(url_for('api_list', project_id=api.project_id))
    form.api_name.data = api.api_name
    form.uri.data = api.uri
    form.method.data = api.method
    form.noises.data = api.noises
    form.order_by.data = api.order_by
    return render_template('edit_api.html', form=form)


@app.route('/api_list/<int:project_id>')
@cache.cached()
def api_list(project_id):
    project = Project.query.get(project_id)
    apis = project.apis
    # if request.iss_xhr:
    # 	return jsonify([(project.id, project.project_name) for project in projects])
    return render_template('api_list.html', apis=apis)


@app.route('/api/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    project = Project.query.get(project_id)
    if project:
        db.session.delete(project)
        db.session.commit()
        return jsonify({'success': 'true'}), 200
    else:
        abort(400)


def get_result_statistics():
    statistics = {
        'dates': [],
        'pass': [],
        'fail': [],
        'percent': []
    }
    today = datetime.date.today()
    for i in range(-8, 1):
        dt = today + datetime.timedelta(days=i)
        total_run = Result.query.filter(db.cast(Result.create_time, db.DATE) == dt)
        total_run_count = total_run.count()
        success_count = total_run.filter(Result.passed == 1).count()
        failed_count = total_run_count - success_count

        percent = round(success_count / total_run_count * 100, 2) if total_run_count != 0 else 0.00
        statistics['dates'].append(dt.strftime('%Y-%m-%-d'))
        statistics['pass'].append(success_count)
        statistics['fail'].append(failed_count)
        statistics['percent'].append(percent)

    return statistics


def get_counts():
    project_count = db.session.query(func.count(Project.id)).scalar()
    task_count = db.session.query(func.count(Task.id)).scalar()
    api_count = db.session.query(func.count(Api.id)).scalar()
    arg_count = db.session.query(func.count(Args.id)).scalar()
    counts = {
        "project_count": project_count,
        "api_count": api_count,
        "task_count": task_count,
        "arg_count": arg_count
    }
    return counts


@app.route('/test')
def test():
    return render_template('ui.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def special_exception_handler(error):
    app.logger.error(error)
    return '请联系管理员', 500


def get_next_url(default='index', **kwargs):
    for url in request.args.get('next'), request.referrer:
        if url:
            return redirect(url)
    return redirect(url_for(default, **kwargs))
