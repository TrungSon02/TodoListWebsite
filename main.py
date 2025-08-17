import time

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column
from sqlalchemy import Integer, String
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, NumberRange
from flask_bootstrap import Bootstrap5
import datetime


app = Flask(__name__)
local_task = []
list_of_main_task = []
list_of_today_task = []
bootstrap = Bootstrap5(app)
app.secret_key = "sub2GSP"
time_choice = ['<15min', '30min', '1 hour', '1h30min', '2 hours', '3 hours', '3+ hour']

def update_percent():
    for task_combo in local_task:
        if len(task_combo["sub_task"]) != 0:
            medium_percent = 100 / len(task_combo["sub_task"])
            total_percent = 0
            for subtask in task_combo["sub_task"]:
                total_percent = total_percent + subtask.progress_bar*medium_percent/ 100
            with app.app_context():
                main_task_to_update = db.get_or_404(Task, task_combo["main_task"].id)
                main_task_to_update.progress_bar = total_percent
                db.session.commit()
def check_datetoday(input_deadline, choice):
    """ Return 1 if the input deadline exceed today's date"""
    today = datetime.datetime.today()
    if choice == "date":
        input_datetime = datetime.datetime(input_deadline.year, input_deadline.month, input_deadline.day)
    else:
        input_datetime = datetime.datetime.strptime(input_deadline, "%Y-%m-%d")

    if input_datetime.year == today.year and input_datetime.month == today.month and input_datetime.day == today.day:
        return 0
    if input_datetime > today:
        return 1
    return -1

def check_2_deadline(main_deadline, sub_deadline):
    """ Return 1 if the sub_deadline exceed main's deadline"""
    main_time = datetime.date(int(main_deadline.split("-")[0]),int(main_deadline.split("-")[1]), int(main_deadline.split("-")[2]))
    print(main_time.year, main_time.month, main_time.day)

    if sub_deadline > main_time:
        return 1
    elif sub_deadline == main_time:
        return 0
    return -1



class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///progress.db"
db = SQLAlchemy(model_class=Base)
db.init_app(app)

class Task(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    deadline: Mapped[str] = mapped_column(String(250), nullable=True, unique=False)
    progress_bar: Mapped[int] = mapped_column(Integer, nullable=False, unique=False)
    parent: Mapped[int] = mapped_column(Integer, unique=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=True)
    duration: Mapped[str] = mapped_column(String(250), nullable=True)
    start_time: Mapped[str] = mapped_column(String(250), nullable=True)
    today: Mapped[int] = mapped_column(Integer, nullable=False)

with app.app_context():
    db.create_all()

def get_task():
    global list_of_main_task, local_task
    local_task = []
    list_of_main_task = []
    with app.app_context():
        result = db.session.execute(db.select(Task).order_by(Task.parent))
        all_tasks = result.scalars().all()

        for task in all_tasks:
            if task.parent != -1:
                break

            temp_subtask_list = [subtask for subtask in all_tasks if subtask.parent == task.id]
            temp_dic = {
                "main_task": task,
                "sub_task": temp_subtask_list,
                "urgency": False,
            }
            if check_datetoday(task.deadline, "string") == 0:
                temp_dic['urgency'] = True
            local_task.append(temp_dic)

    #sorting the deadline in the increasing order
    for i in range(0,len(local_task)):
        for j in range(i+1, len(local_task)):
            if local_task[i]['main_task'].deadline > local_task[j]['main_task'].deadline:
                temp = local_task[i]
                local_task[i] = local_task[j]
                local_task[j] = temp

    for task_combo in local_task:
        for i in range(0, len(task_combo["sub_task"])):
            if check_datetoday(task_combo["sub_task"][i].deadline, "string") == 0:
                task_combo['urgency'] = True

            for j in range(i+1, len(task_combo["sub_task"])):
                if task_combo["sub_task"][i].deadline > task_combo["sub_task"][j].deadline:
                    temp = task_combo["sub_task"][i]
                    task_combo["sub_task"][i] = task_combo["sub_task"][j]
                    task_combo["sub_task"][j] = temp

    #Updating the main task's progress bar
    update_percent()



    list_of_main_task = [temp_task["main_task"].name for temp_task in local_task]

get_task()
class MyForm(FlaskForm):
    name = StringField(label='Name Of The Task', validators=[DataRequired()])
    main_task = SelectField(label='Select The Existing Main Task', choices=list_of_main_task, validate_choice=False)
    deadline = DateField(label='Deadline')
    progress = IntegerField(label="Task's Current Progress", validators=[NumberRange(0,100)])
    submit = SubmitField()


class TodayForm(FlaskForm):
    name = SelectField(label='Select Sub Task', choices=[], validate_choice=False)
    description = StringField(label='What is your approach/What are you gonna do to complete this task?')
    duration = SelectField(label='How long do you want to do this task?', choices=time_choice, validate_choice=False)
    start_time = StringField(label='When do you plan to start this task?')
    submit = SubmitField()

@app.route("/")
@app.route("/home")
def home():
    get_task()
    task_id = request.args.get("task_id")
    delete_type = request.args.get("delete_type")
    return render_template("index.html", local_task=local_task, delete_type=delete_type, task_id=task_id)


@app.route("/add")
def add():
    get_task()
    if not local_task:
        return redirect(url_for('addtask', choice='main'))
    return render_template("add.html")


@app.route("/addtask", methods=["GET", 'POST'])
def addtask():
    form = MyForm(progress=0)
    get_task()
    form.main_task.choices = list_of_main_task
    choice = request.args.get("choice")

    if not form.validate_on_submit() and request.method == "POST":
        if form.main_task.data is None:
            return render_template("addtask.html", form=form, main=True, success=False)
        else:
            return render_template("addtask.html", form=form, main=False, success=False)


    if form.validate_on_submit():
        if check_datetoday(form.deadline.data, "date") == -1:
            form.deadline.errors.append("The date you selected have already passed")
            if form.main_task.data is not None:
                return render_template("addtask.html", form=form, main=False, success=False)
            return render_template("addtask.html", form=form, main=True, success=False)

        parent_id = -1
        if form.main_task.data is not None:
            for task_combo in local_task:
                if task_combo['main_task'].name == form.main_task.data:
                    if check_2_deadline(main_deadline=task_combo['main_task'].deadline, sub_deadline=form.deadline.data) == 1:
                        form.deadline.errors.append("The deadline of the subtask should not exceed the main task's deadline")
                        return render_template("addtask.html", form=form, main=False, success=False)

            for task_combo in local_task:
                if task_combo["main_task"].name == form.main_task.data:
                    parent_id = task_combo["main_task"].id

        with app.app_context():
            new_task = Task(name=form.name.data, deadline=form.deadline.data, progress_bar=0, parent=parent_id, description="", duration="", start_time="", today=0)
            db.session.add(new_task)
            db.session.commit()

        get_task()
        form.main_task.choices = list_of_main_task
        return redirect(url_for('home'))

    if choice == "sub":
        return render_template("addtask.html", form=form, main=False, success=None)
    return render_template("addtask.html", form=form, main=True, success=None)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    task_id = int(request.args.get("task"))
    choice = request.args.get("choice")
    with app.app_context():
        task_to_update = db.get_or_404(Task, task_id)
        deadline_dateObject = datetime.date(int(task_to_update.deadline.split("-")[0]), int(task_to_update.deadline.split("-")[1]), int(task_to_update.deadline.split("-")[2]))
    form = MyForm(name=task_to_update.name, deadline=deadline_dateObject, progress=task_to_update.progress_bar)

    if form.validate_on_submit():
        if task_to_update.name not in list_of_main_task:
            main_task = db.get_or_404(Task, task_to_update.parent)
            maintask_dateObject = datetime.date(int(main_task.deadline.split("-")[0]), int(main_task.deadline.split("-")[1]), int(main_task.deadline.split("-")[2]))
            if maintask_dateObject < form.deadline.data:
                form.deadline.errors.append("The deadline of the subtask should not exceed the main task's deadline")
                return render_template("edit.html", form=form, success=False)

        with app.app_context():
            task_to_update = db.get_or_404(Task, task_id)
            task_to_update.name = form.name.data
            task_to_update.deadline = form.deadline.data
            task_to_update.progress_bar = form.progress.data
            db.session.commit()

        return redirect(url_for('home'))


    return render_template("edit.html", form=form, id=task_to_update.id, choice=choice)


@app.route("/delete")
def delete():
    task_id = int(request.args.get("task_id"))
    delete_type = request.args.get("delete_type")
    if delete_type == "delete2":
        with app.app_context():
            task_to_delete = db.get_or_404(Task, int(task_id))
            if task_to_delete.name in list_of_main_task:
                for task_combo in local_task:
                    if task_combo["main_task"].name == task_to_delete.name:
                        for subtask in task_combo["sub_task"]:
                            with app.app_context():
                                subtask_to_delete = db.get_or_404(Task, subtask.id)
                                db.session.delete(subtask_to_delete)
                                db.session.commit()

            db.session.delete(task_to_delete)
            db.session.commit()
            get_task()
            return redirect(url_for('home'))
    return redirect(url_for('home', delete_type=delete_type, task_id=task_id))


@app.route("/today", methods=["GET", 'POST'])
def today():
    global list_of_today_task
    choice = request.args.get("choice")
    task = request.args.get("task")
    get_task()
    form = TodayForm(start_time="9am")
    # choice = add/form/done_form/finish1/finish2/end/increase/decrease/submit

    if choice == "form":
        for task_combo in local_task:
            if task_combo["main_task"].name == request.args.get("task_name"):
                templist = [subtask.name for subtask in task_combo['sub_task'] if subtask.progress_bar < 100]
                form.name.choices = templist

    elif choice == "finish2":
        with app.app_context():
            finished_task = db.session.execute(db.select(Task).where(Task.name == task)).scalar()
            print(finished_task.name)
            finished_task.today = 0
            finished_task.progress_bar = 100
            db.session.commit()
    elif choice == 'increasing' or choice == 'decreasing':
        with app.app_context():
            changed_task = db.session.execute(db.select(Task).where(Task.name == task)).scalar()
            if choice == 'increasing':
                amount = 10
            else:
                amount = -5
            changed_task.progress_bar = changed_task.progress_bar + amount
            db.session.commit()
            return redirect(url_for('today', choice='end'))
    elif choice == 'submit':
        with app.app_context():
            submitted_task = db.session.execute(db.select(Task).where(Task.name == task)).scalar()
            submitted_task.today = 0
            db.session.commit()

    if form.validate_on_submit():
        with app.app_context():
            today_task = db.session.execute(db.select(Task).where(Task.name == form.name.data)).scalar()
            today_task.description = form.description.data
            today_task.duration = form.duration.data
            today_task.start_time = form.start_time.data
            today_task.today = 1
            db.session.commit()

    with app.app_context():
        list_of_today_task = db.session.execute(db.select(Task).where(Task.today == 1)).scalars().all()


    return render_template("today.html", choice=choice, main_list=list_of_main_task, form=form, list=list_of_today_task, task=task)





if __name__ == "__main__":
    app.run(debug=False)