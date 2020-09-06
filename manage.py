from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from doraemon import app, db
from doraemon.models import Project, Api, Args, Task, Result

migrate = Migrate(app, db)

manager = Manager(app)

manager.add_command('db', MigrateCommand)


@manager.shell
def make_shell_context():
    return dict(app=app, db=db, Project=Project, Api=Api, Args=Args,
                Task=Task, Result=Result)


if __name__ == '__main__':
    manager.run()
