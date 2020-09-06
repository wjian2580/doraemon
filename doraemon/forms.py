from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired

from doraemon.models import Project


class AddProjectForm(FlaskForm):
    project_name = StringField('项目名称', validators=[DataRequired()])
    primary = StringField('基准服务', validators=[DataRequired()])
    secondary = StringField('降噪服务', validators=[DataRequired()])
    candidate = StringField('待测服务', validators=[DataRequired()])
    submit = SubmitField('提交')


class EditProjectForm(AddProjectForm):
    submit = SubmitField('更新', render_kw={"class": "btn btn-default"})


class AddTaskForm(FlaskForm):
    task_name = StringField('任务名称', validators=[DataRequired()])
    project = SelectField('所属项目', coerce=int)
    task_filter = SelectField('所属项目',
                              coerce=int,
                              choices=[
                                  (1, "limit"),
                                  (2, "time range"),
                                  (3, "api list"),
                                  (4, "crontab")
                                ])
    limit = StringField('用例数量')
    submit = SubmitField('提交')

    def __init__(self):
        super(AddTaskForm, self).__init__()
        projects = Project.query.all()
        select_values = [(project.id, project.project_name) for project in projects]
        self.project.choices = select_values


class EditTaskForm(AddTaskForm):
    submit = SubmitField('更新', render_kw={"class": "btn btn-default"})


class EditApiForm(FlaskForm):
    api_name = StringField('接口名称')
    uri = StringField('路径')
    method = StringField('请求方式')
    noises = StringField('噪声')
    order_by = StringField('排序字断')
    submit = SubmitField('更新', render_kw={"class": "btn btn-default"})
