import json
import os.path
import random
import pandas as pd
import smtplib
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from datetime import datetime, timedelta
from celery import Celery
from celery.schedules import crontab

from jinja2 import Template
from flask import Flask, request, session, jsonify
from flask import make_response, send_from_directory, redirect, send_file
from flask_session import Session
from sqlalchemy import and_
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, autoincrement=True, primary_key=True)
    user_name = Column(String, unique=True)
    password = Column(String, nullable=False)
    f_name = Column(String, nullable=False)
    l_name = Column(String)
    email = Column(String, nullable=False, unique=True)


class TaskList(Base):
    __tablename__ = 'tasklist'
    list_id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String, nullable=False)


class TaskCard(Base):
    __tablename__ = 'taskcard'
    card_id = Column(Integer, autoincrement=True, primary_key=True)
    list_id = Column(Integer, ForeignKey(TaskList.list_id), nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=False)
    completed = Column(Boolean, nullable=False)
    created_ts = Column(DateTime, nullable=False)
    modified_ts = Column(DateTime)
    completed_ts = Column(DateTime)
    ovd_cmp = Column(Boolean, default=False)


class UserList(Base):
    __tablename__ = 'user_list'
    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.user_id), nullable=False)
    list_id = Column(Integer, ForeignKey(TaskList.list_id), nullable=False)


# ------------------------------------------------------------------------------------
engine = create_engine('sqlite:///resource_database.sqlite3')
Base.metadata.create_all(engine)
Session_db = sessionmaker(bind=engine)
app = Flask(__name__)
celery = Celery(app.name, backend='redis://localhost:6379', broker='redis://localhost:6379')
celery.conf.update(app.config)
app_email = '21f1000598@student.onlinedegree.iitm.ac.in'
disp_time_format = '%a, %d %b %Y %I:%M %p'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=


def sendmail(recipient, subj, body):
    msg = MIMEMultipart()
    msg['From'] = app_email
    msg['To'] = recipient
    msg['Subject'] = subj
    msg.attach(MIMEText(body, "html"))

    server = smtplib.SMTP(host='localhost', port=1025)
    server.login(app_email, "")
    server.send_message(msg)
    server.quit()

    return True


def authenticate():
    if not session.get('uid'):
        return False
    if not request.cookies.get('uid'):
        return False
    if session.get('uid') != request.cookies.get('uid'):
        return False
    return True


@app.route('/')
def index():
    return redirect('/dashboard') \
        if authenticate() \
        else redirect('/user')


@app.route('/user', methods=['GET', 'POST'])
def user():
    if request.method == 'GET':
        return send_from_directory('static', 'index.html')
    elif request.method == 'POST':
        data = json.loads(request.data)
        db_session = Session_db()
        if data['req'] == 'login':
            usr = db_session.query(User).filter_by(user_name=data['uid']).first()
            db_session.close()
            if usr is None:
                return jsonify({'status': False, 'msg': 'User Not Found'})
            elif usr.password != data['pwd']:
                return jsonify({'status': False, 'msg': 'Incorrect Password'})
            else:
                session['uid'] = data['uid']
                res = make_response(jsonify({'status': True, 'msg': 'Login Successful'}))
                res.set_cookie('f_name', usr.f_name)
                res.set_cookie('l_name', usr.l_name)
                res.set_cookie('uid', usr.user_name)
                return res

        elif data['req'] == 'reg_acc' or data['req'] == 'recov_acc':
            if data['req'] == 'reg_acc':
                r = db_session.query(User).filter_by(user_name=data['uid']).first()
                if r is not None:
                    db_session.close()
                    return jsonify({'status': False, 'msg': 'User not Found'})
                r = db_session.query(User).filter_by(email=data['email']).first()
                if r is not None:
                    db_session.close()
                    return jsonify({'status': False, 'msg': 'Email already in Use'})

            elif data['req'] == 'recov_acc':
                r = db_session.query(User).filter_by(email=data['email']).first()
                if r is None:
                    db_session.close()
                    return jsonify({'status': False, 'msg': 'Email ID not Registered'})

            vcode = str(random.randrange(100000, 1000000))
            sendmail(data['email'], 'Kanban Verification Code',
                     f'''Your Verification Code for Kanban Application is {vcode}.

                          Thanks & Regards,
                          Sarbeswar
                          ''')
            res = make_response(jsonify({'status': True, 'msg': 'Verification Code Sent to Email'}))
            tok = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                          for _ in range(16))
            res.set_cookie('validate', tok, expires=datetime.now() + timedelta(seconds=120))
            session['valid_acc'] = {
                'code': vcode,
                'data': data,
                'validate': tok,
            }
            db_session.close()
            return res

        elif data['req'] == 'valid_acc':
            vac = session.get('valid_acc')
            if vac['code'] != data['vcode']:
                db_session.close()
                return jsonify({'status': False, 'msg': 'Invalid Code'})
            elif request.cookies.get('validate') != vac['validate']:
                db_session.close()
                return jsonify({'status': False, 'msg': 'Something Went Wrong. Try again'})
            data = vac['data']
            if data['req'] == 'reg_acc':
                usr = User(f_name=data['fname'],
                           l_name=data['lname'],
                           user_name=data['uid'],
                           password=data['pwd'],
                           email=data['email'])
                db_session.add(usr)
                db_session.commit()
                db_session.close()
                session['valid_acc'] = None
                return jsonify({'status': True, 'msg': 'Registration Successful'})
            elif data['req'] == 'recov_acc':
                res = make_response(jsonify({'status': True, 'msg': 'Code Validated! Set New Password'}))
                tok = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                              for _ in range(16))
                res.set_cookie('validate', tok, expires=datetime.now() + timedelta(seconds=120))
                session['valid_acc'] = {
                    'validate': tok,
                    'data': data
                }
                db_session.close()
                return res

        elif data['req'] == 'new_pass':
            vac = session.get('valid_acc')
            if request.cookies.get('validate') != vac['validate']:
                db_session.close()
                return jsonify({'status': False, 'msg': 'Something Went Wrong. Try again'})

            r = db_session.query(User).filter_by(email=vac['data']['email']).first()
            r.password = data['newpass']
            db_session.commit()
            db_session.close()
            return jsonify({'status': True, 'msg': 'New Password has been set Successfully'})

        return


@app.route('/formdata', methods=['GET', 'POST'])
def form_data():
    if not authenticate():
        return redirect('/user')

    if request.args['type'] == 'newlist':
        if request.method == 'GET':
            return jsonify({
                'heading': 'Create a New List',
                'fields': [
                    {'name': 'title', 'disp_text': 'List Title', 'disp_ph': 'Enter the List Title',
                     'type': 'text'}
                ],
                'values': {'title': ''}
            })
        elif request.method == 'POST':
            db = Session_db()
            data = json.loads(request.data)
            lst = TaskList(name=data['title'])
            usr = db.query(User).filter_by(user_name=session['uid']).first()
            db.add(lst)
            db.commit()
            usr_lst = UserList(list_id=lst.list_id, user_id=usr.user_id)
            db.add(usr_lst)
            db.commit()
            db.close()
            return jsonify({'status': True, 'msg': 'New List Successfully Created'})
    elif request.args['type'] == 'editlist':
        if request.method == 'GET':
            list_id = request.args['id']
            db = Session_db()
            lst = db.query(TaskList).filter_by(list_id=list_id).first()
            edit_ui = {'heading': 'Edit Task List', 'fields': [
                {'name': 'title', 'disp_text': 'List Title', 'disp_ph': 'Enter the List Title',
                 'type': 'text'}
            ], 'values': {'title': lst.name}}
            db.close()
            return jsonify(edit_ui)
        elif request.method == 'POST':
            db = Session_db()
            data = json.loads(request.data)
            lst = db.query(TaskList).filter_by(list_id=request.args['id']).first()
            lst.name = data['title']
            db.commit()
            db.close()
            return jsonify({'status': True, 'msg': 'List Name has been Changed Successfully'})
    elif request.args['type'] == 'newcard':
        if request.method == 'GET':
            return jsonify({
                'heading': 'Create a New Task',
                'fields': [
                    {'name': 'title', 'disp_text': 'Task Title', 'disp_ph': 'Enter the Task Title',
                     'type': 'text'},
                    {'name': 'content', 'disp_text': 'Task Description',
                     'disp_ph': 'Type the Task Description in Details',
                     'type': 'text'},
                    {'name': 'due', 'disp_text': 'Task Due Date', 'disp_ph': 'Select the Task Due Date',
                     'type': 'datetime-local'},
                ],
                'values': {
                    'title': '', 'content': '', 'due': ''
                }
            })
        elif request.method == 'POST':
            db = Session_db()
            lid = request.args['id']
            data = json.loads(request.data)
            tz = int(request.headers.get('TZ'))
            crd = TaskCard(list_id=lid, title=data['title'],
                           content=data['content'],
                           deadline=datetime.strptime(data['due'], '%Y-%m-%dT%H:%M') + timedelta(minutes=tz),
                           completed=False,
                           created_ts=datetime.utcnow())
            db.add(crd)
            db.commit()
            db.close()
            return jsonify({'status': True, 'msg': 'New Task Successfully Created'})
    elif request.args['type'] == 'editcard':
        if request.method == 'GET':
            card_id = request.args['id']
            db = Session_db()
            tz = timedelta(minutes=int(request.headers.get('TZ')))
            crd = db.query(TaskCard).filter_by(card_id=card_id).first()
            edit_ui = {'heading': 'Edit your Task', 'fields': [
                {'name': 'title', 'disp_text': 'Task Title', 'disp_ph': 'Enter the Task Title',
                 'type': 'text'},
                {'name': 'content', 'disp_text': 'Task Description', 'disp_ph': 'Type the Task Description in Details',
                 'type': 'text'},
                {'name': 'due', 'disp_text': 'Task Due Date', 'disp_ph': 'Select the Task Due Date',
                 'type': 'datetime-local'},
            ], 'values': {
                'title': crd.title,
                'content': crd.content,
                'due': (crd.deadline - tz).strftime('%Y-%m-%dT%H:%M')
            }}
            db.close()
            return jsonify(edit_ui)
        elif request.method == 'POST':
            db = Session_db()
            data = json.loads(request.data)
            tz = int(request.headers.get('TZ'))
            crd = db.query(TaskCard).filter_by(card_id=request.args['id']).first()
            crd.title = data['title']
            crd.content = data['content']
            crd.deadline = datetime.strptime(data['due'], '%Y-%m-%dT%H:%M') + timedelta(minutes=tz)
            crd.modified_ts = datetime.utcnow()
            db.commit()
            db.close()
            return jsonify({'status': True, 'msg': 'Card details edited successfully'})


@app.route('/dashboard')
def home():
    if not authenticate():
        return redirect('/user')
    if request.method == 'GET':
        return send_from_directory('static', 'content.html')


@app.route('/data')
def fetch_data():
    if not authenticate():
        return redirect('/user')

    db = Session_db()
    tz = timedelta(minutes=int(request.headers.get('TZ')))
    if request.args['rtype'] == 'lists':
        usr = db.query(User).filter_by(user_name=session.get('uid')).first()
        t_lists = db.query(TaskList).join(UserList) \
            .filter(UserList.user_id == usr.user_id).all()
        lst = []
        for t in t_lists:
            cards = db.query(TaskCard).filter_by(list_id=t.list_id)
            r_card = cards.filter_by(completed=False).order_by(TaskCard.deadline).first()
            c_cards = cards.filter_by(completed=True)
            lst.append({'id': t.list_id, 'title': t.name, 'n_cards': cards.count(), 'c_cards': c_cards.count(),
                        'deadline': (r_card.deadline - tz).strftime(disp_time_format) if r_card else None,
                        'cont_overdue': r_card.deadline < datetime.utcnow() if r_card else None})
        db.close()
        return jsonify(lst)

    elif request.args['rtype'] == 'cards':
        lid = request.args['id']
        db = Session_db()
        crds = db.query(TaskCard).filter_by(list_id=lid).all()
        cards = []
        for crd in crds:
            overdue = divmod((datetime.utcnow() - crd.deadline).total_seconds(), 3600)
            cards.append({'id': crd.card_id, 'list_id': crd.list_id, 'title': crd.title,
                          'content': crd.content, 'due': (crd.deadline - tz).strftime(disp_time_format),
                          'created': (crd.created_ts - tz).strftime(disp_time_format),
                          'modified': (crd.modified_ts - tz).strftime(disp_time_format)
                          if crd.modified_ts else None,
                          'completed': crd.completed,
                          'completed_ts': (crd.completed_ts - tz).strftime(disp_time_format)
                          if crd.completed_ts else None,
                          'overdue': datetime.utcnow() > crd.deadline,
                          'overdue_delta_h': overdue[0],
                          'overdue_delta_m': divmod(overdue[1], 60)[0]})
        db.close()
        return jsonify(cards)


@app.route('/card', methods=['POST'])
def card():
    if not authenticate():
        return redirect('/user')
    data = json.loads(request.data)
    if request.args['rtype'] == 'complete':
        db = Session_db()
        c = db.query(TaskCard).filter_by(card_id=data['id']).first()
        c.completed = True
        now = datetime.utcnow()
        c.completed_ts = now
        c.ovd_cmp = now > c.deadline
        db.commit()
        db.close()
        return jsonify({'status': True, 'msg': 'Task Completed'})
    elif request.args['rtype'] == 'delete':
        db = Session_db()
        db.query(TaskCard).filter_by(card_id=data['id']).delete()
        db.commit()
        db.close()
        return jsonify({'status': True, 'msg': 'Task Successfully Deleted'})
    elif request.args['rtype'] == 'move':
        db = Session_db()
        c = db.query(TaskCard).filter_by(card_id=data['id']).first()
        c.list_id = data['list_id']
        db.commit()
        lst = db.query(TaskList).filter_by(list_id=data['list_id']).first()
        db.close()
        return jsonify({'status': True, 'msg': f'Moved the Card to {lst.name}'})


@app.route('/summary')
def summary():
    if not authenticate():
        return redirect('/user')
    return send_from_directory('static', 'summary.html')


def ts_format(r, t):
    if t == 'month':
        if r == 'month' or r == 'week':
            return '%b %d'
    elif t == 'week':
        if r == 'week' or r == 'day':
            return '%a, %b %d'
    elif t == 'day':
        if r == 'day' or r == 'hour':
            return '%a, %H:%M'
    elif t == 'hour' and r == 'hour':
        return '%H:%M'
    return None


@app.route('/summary/data', methods=['POST'])
def summary_data():
    if not authenticate():
        return redirect('/user')
    db = Session_db()

    data = json.loads(request.data)
    tz = timedelta(minutes=int(request.headers.get('TZ')))
    lid = 'all'
    if data['id']:
        lid = data['id']

    duration = timedelta(weeks=1)
    res = timedelta(days=1)
    time_series = []
    frequency = {}
    tsf = ts_format(data['runit'], data['tunit'])
    if not tsf:
        return make_response('Bad Request. Either Reduce the Duration unit or Increase the Interval unit', 400)

    rc = int(data['rscale'])
    if data['runit'] == 'hour':
        res = timedelta(hours=rc)
    elif data['runit'] == 'day':
        res = timedelta(days=rc)
    elif data['runit'] == 'week':
        res = timedelta(weeks=rc)
    elif data['runit'] == 'month':
        res = timedelta(days=30 * rc)

    timeline = int(data['tscale'])
    if data['tunit'] == 'hour':
        duration = timedelta(hours=timeline)
    elif data['tunit'] == 'day':
        duration = timedelta(days=timeline)
    elif data['tunit'] == 'week':
        duration = timedelta(weeks=timeline)
    elif data['tunit'] == 'month':
        duration = timedelta(days=30 * timeline)

    tasks = db.query(TaskCard)
    if lid != 'all':
        tasks = tasks.filter_by(list_id=lid)

    if request.args['scope'] == 'past':
        rtime = datetime.utcnow()
        time = rtime - duration
        time_series.append(time)
        while time < rtime:
            time = time + res
            time_series.append(time)
        frequency['created'] = []
        for t in range(1, len(time_series)):
            fr = tasks.filter(and_(TaskCard.created_ts >= time_series[t - 1],
                                   TaskCard.created_ts < time_series[t])).count()
            frequency['created'].append(fr)
        frequency['completed'] = []
        for t in range(1, len(time_series)):
            fr = tasks.filter(and_(TaskCard.completed_ts >= time_series[t - 1],
                                   TaskCard.completed_ts < time_series[t])).count()
            frequency['completed'].append(fr)
    elif request.args['scope'] == 'upcoming':
        rtime = datetime.utcnow()
        time = rtime + duration
        time_series.append(rtime)
        while rtime < time:
            rtime = rtime + res
            time_series.append(rtime)
        frequency['due'] = []
        for t in range(1, len(time_series)):
            fr = tasks.filter(and_(TaskCard.deadline >= time_series[t - 1],
                                   TaskCard.deadline < time_series[t])).count()
            frequency['due'].append(fr)
        frequency['completed'] = []
        for t in range(1, len(time_series)):
            fr = tasks.filter(and_(TaskCard.deadline >= time_series[t - 1],
                                   TaskCard.deadline < time_series[t])).filter(TaskCard.completed).count()
            frequency['completed'].append(fr)

    db.close()
    return jsonify({'time_series': list(map(lambda ts: (ts - tz).strftime(tsf), time_series)),
                    'frequency': frequency})


@app.route('/download')
def download():
    if not authenticate():
        return redirect('/user')
    pcsv = prepare_csv.apply_async(args=[session.get('uid'),
                                         int(request.headers.get('TZ'))])
    return jsonify({'id': pcsv.id, 'status': True,
                    'msg': 'Request submitted. Starting download in a while'})


@app.route('/download_status', methods=['POST'])
def dst():
    if not authenticate():
        return redirect('/user')
    tid = json.loads(request.data)['id']
    task = celery.AsyncResult(tid)
    if task.ready():
        return send_file(os.path.join('generated', 'tasks.csv'), download_name='tasks.csv', as_attachment=True)
    else:
        return make_response('', 202)


@app.route('/logout')
def logout():
    session['uid'] = None
    res = make_response()
    res.delete_cookie('f_name')
    res.delete_cookie('l_name')
    res.delete_cookie('uid')
    return res


@celery.task
def prepare_csv(user_name, tz_offset):
    data = []
    tz = timedelta(minutes=tz_offset)
    db = Session_db()
    usr = db.query(User).filter_by(user_name=user_name).first()
    lists = db.query(TaskList).join(UserList) \
        .filter(UserList.user_id == usr.user_id).all()
    for lst in lists:
        crds = db.query(TaskCard).filter_by(list_id=lst.list_id).all()
        for crd in crds:
            if crd.ovd_cmp:
                status = 'Finished Late'
            elif crd.completed:
                status = 'Completed'
            elif crd.deadline < datetime.utcnow():
                status = 'Overdue'
            else:
                status = 'Assigned'
            dlist = {'List Name': lst.name, 'Task Name': crd.title,
                     'Created': (crd.created_ts - tz).strftime(disp_time_format),
                     'Deadline': (crd.deadline - tz).strftime(disp_time_format),
                     'Completed TimeStamp': (crd.completed_ts - tz).strftime(disp_time_format)
                     if crd.completed_ts else None,
                     'Last Modified': (crd.modified_ts - tz).strftime(disp_time_format)
                     if crd.modified_ts else None,
                     'Status': status}
            data.append(dlist)
    db.close()
    pd.DataFrame(data).to_csv('generated/tasks.csv', index=False)


@celery.task
def send_reminder(scope):
    db = Session_db()
    users = db.query(User).all()
    tScope = timedelta(days=1)
    heading = ''
    desc = ''
    if scope == 'Daily':
        heading = 'Tasks Due By Tomorrow'
        desc = 'Finished these tasks? Submit them by tomorrow. Not yet? Come on, Work on these tasks! You got this!'
    elif scope == 'Weekly':
        tScope = timedelta(weeks=1)
        heading = 'Tasks Due By Next Week'
        desc = 'When are you planning to clear these tasks? This is just a reminder. ' \
               'Have a look at the tasks due in next week'

    for usr in users:
        Headers = ['List', 'Task Name', 'Created (UTC)', 'Due (UTC)']
        Data = []
        lists = db.query(TaskList).join(UserList) \
            .filter(UserList.user_id == usr.user_id).all()
        for lst in lists:
            crds = db.query(TaskCard).filter_by(list_id=lst.list_id).all()
            for crd in crds:
                if (not crd.completed) and crd.deadline <= datetime.utcnow() + tScope:
                    Data.append([lst.name, crd.title,
                                 crd.created_ts.strftime(disp_time_format),
                                 crd.deadline.strftime(disp_time_format)])
        msg_temp = open("templates/msg_table.html", 'r').read()
        temp = Template(msg_temp)
        html_body = temp.render(heading=heading, desc=desc, headers=Headers, data=Data)
        if len(Data) > 0:
            sendmail(usr.email, f'{scope} Task Reminder', html_body)
    db.close()


@celery.task
def last_hour_reminder():
    db = Session_db()
    users = db.query(User).all()
    for usr in users:
        lists = db.query(TaskList).join(UserList) \
            .filter(UserList.user_id == usr.user_id).all()
        for lst in lists:
            crds = db.query(TaskCard).filter_by(list_id=lst.list_id).all()
            for crd in crds:
                now = datetime.utcnow()
                if (not crd.completed) and now + timedelta(hours=1) <= crd.deadline \
                        < now + timedelta(hours=1, minutes=1):
                    sendmail(usr.email, f'[Important] Task Due Reminder',
                             f'''
                             <h1>Tasks Due within Next Hour</h1>
                             <p>The Task "{crd.title}" from the Task List "{lst.name}" is about to overdue in an hour!
                             Please complete it ASAP.</p>
                             <p>Otherwise, you can always edit and extend the deadlines. 
                             Go to the application to manage.</p>
                            ''')
    db.close()


@celery.task
def progress_report():
    db = Session_db()
    users = db.query(User).all()
    heading = f"Monthly Progress Report of {(datetime.utcnow() - timedelta(days=1)).strftime('%B, %Y')}"
    desc = 'Please find the Progress Report as follows'

    for usr in users:
        now = datetime.utcnow()
        Headers = ['Parameters', 'Tasks']
        Data = []
        tasks = db.query(TaskCard).join(TaskList).join(UserList).filter(UserList.user_id == usr.user_id)
        Data.append(['Number of Tasks', tasks.count()])
        Data.append(['New Tasks Created',
                     tasks.filter(and_(TaskCard.created_ts < now,
                                       TaskCard.created_ts >= now - timedelta(days=30))).count()])
        Data.append(['Tasks Completed', tasks.filter(and_(TaskCard.completed_ts < now,
                                                          TaskCard.completed_ts >= now - timedelta(days=30))).count()])
        Data.append(['Overdue Tasks', tasks.filter(TaskCard.completed==False).filter(now > TaskCard.deadline).count()])
        Data.append(['Tasks Completed Past Deadline', tasks.filter(TaskCard.ovd_cmp).count()])

        msg_temp = open("templates/msg_table.html", 'r').read()
        temp = Template(msg_temp)
        html_body = temp.render(heading=heading, desc=desc, headers=Headers, data=Data)
        sendmail(usr.email, 'Monthly Progress Report', html_body)
    db.close()


# ------------------------------------------------------------------------------------
celery.conf.beat_schedule = {
    'daily': {
        'task': f'{app.name}.send_reminder',
        'schedule': crontab(minute=0, hour=21),
        'args': ['Daily']
    },
    'weekly': {
        'task': f'{app.name}.send_reminder',
        'schedule': crontab(minute=0, hour=21, day_of_week='sunday'),
        'args': ['Weekly']
    },
    'last_hour_reminder': {
        'task': f'{app.name}.last_hour_reminder',
        'schedule': crontab(),
        'args': []
    },
    'monthly_report': {
        'task': f'{app.name}.progress_report',
        'schedule': crontab(minute=0, hour=0, day_of_month=1),
        'args': []
    }
}
celery.conf.timezone = 'UTC'
if __name__ == '__main__':
    app.run()
