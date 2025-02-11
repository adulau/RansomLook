from flask import Flask, render_template, redirect, url_for, flash
import flask_moment # type: ignore
from flask import request
from flask_bootstrap import Bootstrap5  # type: ignore

from datetime import datetime as dt
import glob
from os.path import dirname, basename, isfile, join
import os
import json
from redis import Redis

import ast
import flask_login  # type: ignore
from werkzeug.security import check_password_hash

from flask_cors import CORS  # type: ignore
from flask_restx import Api  # type: ignore

from importlib.metadata import version

from collections import OrderedDict

from ransomlook.ransomlook import adder
from ransomlook.sharedutils import createfile
from ransomlook.sharedutils import groupcount, hostcount, onlinecount, postslast24h, mounthlypostcount, currentmonthstr, postssince, poststhisyear,postcount,parsercount
from ransomlook.default.config import get_homedir
from ransomlook.default import get_socket_path
from ransomlook.telegram import teladder
from .helpers import get_secret_key, sri_load, User, build_users_table, load_user_from_request
from .forms import AddForm, LoginForm, SelectForm, EditForm, DeleteForm, AlertForm

from .genericapi import api as generic_api

app = Flask(__name__)

app.config['SECRET_KEY'] = get_secret_key()

Bootstrap5(app)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
app.config['SESSION_COOKIE_NAME'] = 'ransomlook'
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'

pkg_version = version('ransomlook')

flask_moment.Moment(app=app)

# Auth stuff
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def user_loader(username):
    if username not in build_users_table():
        return None
    user = User()
    user.id = username
    return user


@login_manager.request_loader
def _load_user_from_request(request):
    return load_user_from_request(request)


@app.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        users_table = build_users_table()
        if username in users_table and check_password_hash(users_table[username]['password'], form.password.data):
            user = User()
            user.id = username
            flask_login.login_user(user)
            flash(f'Logged in as: {flask_login.current_user.id}', 'success')
            return redirect(url_for('admin'))
        else:
            flash(f'Unable to login as: {username}', 'error')
    return render_template('login.html', form=form)


@app.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    flash('Successfully logged out.', 'success')
    return redirect(url_for('home'))

# End auth

def get_sri(directory: str, filename: str) -> str:
    sha512 = sri_load()[directory][filename]
    return f'sha512-{sha512}'

app.jinja_env.globals.update(get_sri=get_sri)

def suffix(d: int) -> str :
    return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

def custom_strftime(fmt, t):
    return t.strftime(fmt).replace('{S}', str(t.day) + suffix(t.day))

@app.route('/')
def home():
        date = custom_strftime('%B {S}, %Y', dt.now()).lower()
        data = {}
        data['nbgroups'] = groupcount()
        data['nblocations'] = hostcount()
        data['online'] = onlinecount()
        data['24h'] = postslast24h()
        data['monthlypost'] = mounthlypostcount()
        data['month'] = currentmonthstr() # type: ignore
        data['90d'] = postssince(90)
        data['yearlypost'] = poststhisyear()
        data['year'] = dt.now().year
        data['nbposts'] = postcount()
        data['nbparsers'] = parsercount()
        return render_template("index.html", date=date, data=data)

@app.route("/recent")
def recent():
        posts = []
        red = Redis(unix_socket_path=get_socket_path('cache'), db=2)
        for key in red.keys():
                entries = json.loads(red.get(key)) # type: ignore
                for entry in entries:
                    entry['group_name']=key.decode()
                    posts.append(entry)
        sorted_posts = sorted(posts, key=lambda x: x['discovered'], reverse=True)
        recentposts = []
        for post in sorted_posts:
                recentposts.append(post)
                if len(recentposts) == 100:
                        break
        return render_template("recent.html", data=recentposts)

@app.route("/status")
def status():
        red = Redis(unix_socket_path=get_socket_path('cache'), db=0)
        groups = []
        for key in red.keys():
                entry= json.loads(red.get(key)) # type: ignore
                entry['name']=key.decode()
                groups.append(entry)
        groups.sort(key=lambda x: x["name"].lower())
        for group in groups:
            for location in group['locations']:
                screenfile = '/screenshots/' + group['name'] + '-' + createfile(location['slug']) + '.png'
                if os.path.exists(str(get_homedir()) + '/source' + screenfile):
                    location['screen']=screenfile
        red = Redis(unix_socket_path=get_socket_path('cache'), db=3)
        markets = []
        for key in red.keys():
                entry= json.loads(red.get(key)) # type: ignore
                entry['name']=key.decode()
                markets.append(entry)
        markets.sort(key=lambda x: x["name"].lower())
        for group in markets:
            for location in group['locations']:
                screenfile = '/screenshots/' + group['name'] + '-' + createfile(location['slug']) + '.png'
                if os.path.exists(str(get_homedir()) + '/source' + screenfile):
                    location['screen']=screenfile

        return render_template("status.html", data=groups, markets=markets)

@app.route("/alive")

def alive():
        red = Redis(unix_socket_path=get_socket_path('cache'), db=0)
        groups = []
        for key in red.keys():
                entry= json.loads(red.get(key)) # type: ignore
                entry['name']=key.decode()
                groups.append(entry)
        groups.sort(key=lambda x: x["name"].lower())
        for group in groups:
            for location in group['locations']:
                screenfile = '/screenshots/' + group['name'] + '-' + createfile(location['slug']) + '.png'
                if os.path.exists(str(get_homedir()) + '/source' + screenfile):
                    location['screen']=screenfile
        red = Redis(unix_socket_path=get_socket_path('cache'), db=3)
        markets = []
        for key in red.keys():
                entry= json.loads(red.get(key)) # type: ignore
                entry['name']=key.decode()
                markets.append(entry)
        markets.sort(key=lambda x: x["name"].lower())
        for group in markets:
            for location in group['locations']:
                screenfile = '/screenshots/' + group['name'] + '-' + createfile(location['slug']) + '.png'
                if os.path.exists(str(get_homedir()) + '/source' + screenfile):
                    location['screen']=screenfile

        return render_template("alive.html", data=groups, markets=markets)


@app.route("/groups")
def groups():
        red = Redis(unix_socket_path=get_socket_path('cache'), db=0)
        redpost = Redis(unix_socket_path=get_socket_path('cache'), db=2)

        groups = []
        for key in red.keys():
                entry= json.loads(red.get(key)) # type: ignore
                entry['name']=key.decode()
                if key in redpost.keys():
                    posts=json.loads(redpost.get(key)) # type: ignore
                    sorted_posts = sorted(posts, key=lambda x: x['discovered'], reverse=True)
                    entry['posts']= sorted_posts
                else:
                    entry['posts']={}
                groups.append(entry)
        groups.sort(key=lambda x: x["name"].lower())
        for group in groups:
            for location in group['locations']:
                screenfile = '/screenshots/' + group['name'] + '-' + createfile(location['slug']) + '.png'
                if os.path.exists(str(get_homedir()) + '/source' + screenfile):
                    location['screen']=screenfile
        modules = glob.glob(join(dirname(str(get_homedir())+'/ransomlook/parsers/'), "*.py"))
        parserlist = [ basename(f)[:-3].split('.')[0] for f in modules if isfile(f) and not f.endswith('__init__.py')]
        return render_template("groups.html", data=groups, parser=parserlist)

@app.route("/group/<name>")
def group(name):
        red = Redis(unix_socket_path=get_socket_path('cache'), db=0)
        groups = []
        for key in red.keys():
                if key.decode().lower() == name.lower():
                        group= json.loads(red.get(key)) # type: ignore
                        group['name']=key.decode()
                        if group['meta'] is not None:
                            group['meta']=group['meta'].replace('\n', '<br/>')
                        for location in group['locations']:
                            screenfile = '/screenshots/' + group['name'] + '-' + createfile(location['slug']) + '.png'
                            if os.path.exists(str(get_homedir()) + '/source' + screenfile):
                                location['screen']=screenfile
                        redpost = Redis(unix_socket_path=get_socket_path('cache'), db=2)
                        if key in redpost.keys():
                            posts=json.loads(redpost.get(key)) # type: ignore
                            sorted_posts = sorted(posts, key=lambda x: x['discovered'], reverse=True)
                        else:
                            sorted_posts = []
                        return render_template("group.html", group = group, posts=sorted_posts)

        return redirect(url_for("home"))

@app.route("/markets")
def markets():
        red = Redis(unix_socket_path=get_socket_path('cache'), db=3)
        redpost = Redis(unix_socket_path=get_socket_path('cache'), db=2)

        groups = []
        for key in red.keys():
                entry= json.loads(red.get(key)) # type: ignore
                entry['name']=key.decode()
                if key in redpost.keys():
                    posts=json.loads(redpost.get(key)) # type: ignore
                    sorted_posts = sorted(posts, key=lambda x: x['discovered'], reverse=True)
                    entry['posts']= sorted_posts
                else:
                    entry['posts']={}
                groups.append(entry)
        groups.sort(key=lambda x: x["name"].lower())
        for group in groups:
            for location in group['locations']:
                screenfile = '/screenshots/' + group['name'] + '-' + createfile(location['slug']) + '.png'
                if os.path.exists(str(get_homedir()) + '/source' + screenfile):
                    location['screen']=screenfile
        modules = glob.glob(join(dirname(str(get_homedir())+'/ransomlook/parsers/'), "*.py"))
        parserlist = [ basename(f)[:-3].split('.')[0] for f in modules if isfile(f) and not f.endswith('__init__.py')]
        return render_template("groups.html", data=groups, parser=parserlist)

@app.route("/market/<name>")
def market(name):
        red = Redis(unix_socket_path=get_socket_path('cache'), db=3)
        groups = []
        for key in red.keys():
                if key.decode().lower() == name.lower():
                        group= json.loads(red.get(key)) # type: ignore
                        group['name']=key.decode()
                        redpost = Redis(unix_socket_path=get_socket_path('cache'), db=2)
                        if key in redpost.keys():
                            posts=json.loads(redpost.get(key)) # type: ignore
                            sorted_posts = sorted(posts, key=lambda x: x['discovered'], reverse=True)
                        else:
                            sorted_posts = []
                        return render_template("group.html", group = group, posts=sorted_posts)
        return redirect(url_for("home"))

@app.route("/leaks")
def leaks():
        red = Redis(unix_socket_path=get_socket_path('cache'), db=4)

        leaks = []
        for key in red.keys():
                entry= json.loads(red.get(key)) # type: ignore
                entry['id']=key
                leaks.append(entry)
        leaks.sort(key=lambda x: x["name"].lower())
        return render_template("leaks.html", data=leaks)

@app.route("/leak/<name>")
def leak(name):
        red = Redis(unix_socket_path=get_socket_path('cache'), db=4)
        groups = []
        for key in red.keys():
                if key.decode().lower() == name.lower():
                        group= json.loads(red.get(key)) # type: ignore
                        if 'meta' in group and group['meta'] is not None:
                            group['meta']=group['meta'].replace('\n', '<br/>')
                        return render_template("leak.html", group = group)

        return redirect(url_for("home"))

@app.route("/telegrams")
def telegrams():
        red = Redis(unix_socket_path=get_socket_path('cache'), db=5)

        telegram = []
        for key in red.keys():
                entry= json.loads(red.get(key)) # type: ignore
                screenfile = '/screenshots/telegram/' + entry['name'] + '.png'
                if os.path.exists(str(get_homedir()) + '/source' + screenfile):
                    entry['screen']=screenfile
                telegram.append(entry)
        telegram.sort(key=lambda x: x["name"].lower())
        return render_template("telegrams.html", data=telegram)

@app.route("/telegram/<name>")
def telegram(name):
        red = Redis(unix_socket_path=get_socket_path('cache'), db=6)
        groups = []
        for key in red.keys():
                if key.decode() == name:
                        posts= json.loads(red.get(key)) # type: ignore
                        return render_template("telegram.html", posts = posts, name=name)

        return redirect(url_for("home"))

@app.route("/crypto")
def crypto():
        red = Redis(unix_socket_path=get_socket_path('cache'), db=7)
        groups = {}
        for key in red.keys():
                groups[key.decode()]=json.loads(red.get(key)) # type: ignore
        crypto = OrderedDict(sorted(groups.items()))
        return render_template("crypto.html", data=crypto)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('search')
        red = Redis(unix_socket_path=get_socket_path('cache'), db=0)
        groups = []
        for key in red.keys():
            group = json.loads(red.get(key)) # type: ignore
            if query.lower() in key.decode().lower() or group['meta'] is not None and query.lower() in group['meta'].lower(): # type: ignore
                group['name']=key.decode().lower()
                groups.append(group)
        groups.sort(key=lambda x: x["name"].lower())

        red = Redis(unix_socket_path=get_socket_path('cache'), db=3)
        markets = []
        for key in red.keys():
            group = json.loads(red.get(key)) # type: ignore
            if query.lower() in key.decode().lower() or group['meta'] is not None and query.lower() in group['meta'].lower(): # type: ignore
                group['name'] = key.decode().lower()
                markets.append(group)
        markets.sort(key=lambda x: x["name"].lower())

        red = Redis(unix_socket_path=get_socket_path('cache'), db=4)
        leaks = []
        for key in red.keys():
            group = json.loads(red.get(key)) # type: ignore
            if query.lower() in key.decode().lower() or group['meta'] is not None and query.lower() in group['meta'].lower(): # type: ignore
                group['name'] = key.decode().lower()
                leaks.append(group)
        leaks.sort(key=lambda x: x["name"].lower())

        red = Redis(unix_socket_path=get_socket_path('cache'), db=2)
        posts = []
        for key in red.keys():
                entries = json.loads(red.get(key)) # type: ignore
                for entry in entries:
                    if query.lower() in entry['post_title'].lower() or 'description' in entry and entry['description'] is not None and query.lower() in entry['description'].lower(): # type: ignore
                        entry['group_name']=key.decode()
                        posts.append(entry)
        posts.sort(key=lambda x: x["group_name"].lower())

        red = Redis(unix_socket_path=get_socket_path('cache'), db=5)
        channels = []
        for key in red.keys():
            group = json.loads(red.get(key)) # type: ignore
            if query.lower() in key.decode().lower() or group['meta'] is not None and query.lower() in group['meta'].lower(): # type: ignore
                channels.append(group)
        channels.sort(key=lambda x: x["name"].lower())

        red = Redis(unix_socket_path=get_socket_path('cache'), db=6)
        messages = []
        for key in red.keys():
                entries = json.loads(red.get(key)) # type: ignore
                for entry in entries:
                    if query.lower() in entries[entry].lower() : # type: ignore
                        myentry={}
                        myentry["group_name"] = key.decode()
                        myentry["message"] = entries[entry]
                        messages.append(myentry)
        messages.sort(key=lambda x: x["group_name"].lower())

        return render_template("search.html", query=query,groups=groups, markets=markets, posts=posts, leaks=leaks, channels=channels, messages=messages)
    return redirect(url_for("home"))

# Admin Zone

@app.route('/admin/')
@app.route('/admin')
@flask_login.login_required
def admin():
    return render_template('admin.html')

@app.route('/admin/add', methods=['GET', 'POST'])
@flask_login.login_required
def addgroup():
    score = int(round(dt.now().timestamp()))
    form = AddForm()
    if form.validate_on_submit():
        if int(form.category.data) == 5:
           res = teladder(form.groupname.data, form.url.data)
        else:
           res = adder(form.groupname.data.lower(), form.url.data, form.category.data)
        if res > 1:
           flash(f'Fail to add: {form.url.data} to {form.groupname.data}.  Url already exists for this group', 'error')
           return render_template('add.html',form=form)
        else:
           flash(f'Success to add: {form.url.data} to {form.groupname.data}', 'success')
           redlogs = Redis(unix_socket_path=get_socket_path('cache'), db=1)
           redlogs.zadd("logs", {f"{flask_login.current_user.id} add : {form.groupname.data}, {form.url.data}": score})
           return redirect(url_for('admin'))
    return render_template('add.html',form=form)

@app.route('/admin/edit', methods=['GET', 'POST'])
@flask_login.login_required
def edit():
    formSelect = SelectForm()
    formMarkets = SelectForm()
    red = Redis(unix_socket_path=get_socket_path('cache'), db=0)
    keys = red.keys()
    choices=[('','Please select your group')]
    keys.sort(key=lambda x: x.lower())
    for key in keys:
        choices.append((key.decode(), key.decode()))
    formSelect.group.choices=choices

    red = Redis(unix_socket_path=get_socket_path('cache'), db=3)
    keys = red.keys()
    choices=[('','Please select your group')]
    keys.sort(key=lambda x: x.lower())
    for key in keys:
        choices.append((key.decode(), key.decode()))
    formMarkets.group.choices=choices

    if formSelect.validate_on_submit():
        return redirect('/admin/edit/'+'0'+'/'+formSelect.group.data)
    if formMarkets.validate_on_submit():
        return redirect('/admin/edit/'+'3'+'/'+formMarkets.group.data)
    return render_template('edit.html', form=formSelect, formMarkets=formMarkets)

@app.route('/admin/edit/<database>/<name>', methods=['GET', 'POST'])
@flask_login.login_required
def editgroup(database, name):
    score = dt.now().timestamp()
    deleteButton = DeleteForm()
    form = EditForm()
    red = Redis(unix_socket_path=get_socket_path('cache'), db=database)
    redlogs = Redis(unix_socket_path=get_socket_path('cache'), db=1)
    if deleteButton.validate_on_submit():
        red.delete(name)
        redlogs.zadd('logs', {f'{flask_login.current_user.id} deleted : {name}': score})
        flash(f'Success to delete : {name}', 'success')
        return redirect(url_for('admin'))
    if form.validate_on_submit():
        data = json.loads(red.get(name)) # type: ignore
        data['meta']=form.description.data
        data['profile'] = ast.literal_eval(form.profiles.data)
        data['locations'] = ast.literal_eval(form.links.data)
        red.set(name, json.dumps(data))
        redlogs.zadd('logs', {f'{flask_login.current_user.id} modified : {name}, {data["meta"]}, {data["profile"]}, {data["locations"]}': score})
        if name != form.groupname.data:
            red.rename(name, form.groupname.data.lower())
            redlogs.zadd('logs', {f'{flask_login.current_user.id} renamed : {name} to {form.groupname.data}': score})
        flash(f'Success to edit : {form.groupname.data}', 'success')
        return redirect(url_for('admin'))
    form.groupname.label=name
    form.groupname.data=name
    data = json.loads(red.get(name)) # type: ignore
    if form.description.data == None:
        form.description.data = data['meta']
    if form.profiles.data == None:
        form.profiles.data = data['profile']
    if form.links.data == None:
        if data['locations']== '':
            data['locations']='[]'
        form.links.data = data['locations']
    return render_template('editentry.html', form=form, deleteform=deleteButton)

@app.route('/export/<database>')
def exportdb(database):
    if database not in ['0','2','3','4','5','6']:
        flash(f'You are not allowed to dump this DataBase', 'error')
        return redirect(url_for('home'))
    red = Redis(unix_socket_path=get_socket_path('cache'), db=database)
    dump={}
    for key in red.keys():
        dump[key.decode()]=json.loads(red.get(key)) # type: ignore
    return dump

@app.route('/admin/logs')
@flask_login.login_required
def logs():
    red = Redis(unix_socket_path=get_socket_path('cache'), db=1)
    logs = red.zrange('logs', 0, -1, desc=True, withscores=True)
    log = []
    for i,s in enumerate(logs):
       log.append((s[0].decode(), dt.fromtimestamp(s[1]).strftime('%Y-%m-%d')))
    return render_template('logs.html', logs=log)

@app.route('/admin/alerting', methods=['GET', 'POST'])
@flask_login.login_required
def alerting():
    form = AlertForm()
    red = Redis(unix_socket_path=get_socket_path('cache'), db=1)
    keywordsred = red.get('keywords')
    keywords= None
    if keywordsred is not None:
        keywords = keywordsred.decode()
    if form.validate_on_submit():
        keywordstmp = str(form.keywords.data).splitlines()
        keywordslist = list(dict.fromkeys(keywordstmp))
        keywords = '\n'.join(keywordslist)
        red.set('keywords',str(keywords))
        flash(f'Success to update keywords', 'success')
    form.keywords.data=keywords
    return render_template('alerts.html', form=form)

if __name__ == "__main__":
	app.run(debug=True)


authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    }
}

api = Api(app, title='RansomLook API',
          description='API to submit captures and query a RansomLook instance.',
          doc='/doc/',
          authorizations=authorizations,
          version=pkg_version)

api.add_namespace(generic_api)
