# -*- coding: utf-8 -*-

__all__ = ()

import datetime

import time
import json
import string
import random
import timeago
import requests
import flask
from flask import flash
from flask import jsonify
from flask import request
from quart import Blueprint
from quart import render_template
from quart import session
from quart import request
from quart import redirect
from quart import url_for

from objects import glob
from objects.utils import flash
from objects.privileges import Privileges
from objects.utils import get_safe_name

admin = Blueprint('admin', __name__)

@admin.route('/')
@admin.route('/home')
@admin.route('/dashboard')
async def home():
    """Render the homepage of guweb's admin panel."""
    if not 'authenticated' in session:
        return await flash('error', 'Please login first.', 'login')

    if not session['user_data']['is_staff'] and not session['user_data']['is_nominator']:
        return await flash('error', f'You have insufficient privileges.', 'home')

    # fetch data from database
    dash_data = await glob.db.fetch(
        'SELECT COUNT(id) count, '
        '(SELECT name FROM users ORDER BY id DESC LIMIT 1) lastest_user, '
        '(SELECT COUNT(id) FROM users WHERE NOT priv & 1) banned '
        'FROM users'
    )

    recent_users = await glob.db.fetchall('SELECT * FROM users ORDER BY id DESC LIMIT 5')
    recent_scores = await glob.db.fetchall(
        'SELECT scores.*, maps.artist, maps.title, '
        'maps.set_id, maps.creator, maps.version '
        'FROM scores JOIN maps ON scores.map_md5 = maps.md5 '
        'ORDER BY scores.id DESC LIMIT 5'
    )

    admin_data = await glob.db.fetch(
        'SELECT id, safe_name, name, priv '
        'FROM users '
        'WHERE %s ',
        [session['user_data']['id']]
    )

    score_count = await glob.db.fetch('SELECT MAX(id) AS max_id FROM scores')

    return await render_template(
    'admin/home.html',
        dashdata=dash_data,
        recentusers=recent_users,
        recentscores=recent_scores,
        datetime=datetime,
        timeago=timeago,
        admin_data=admin_data,
        score_count=score_count
    )

@admin.route('/users/')
async def users():
    if not 'authenticated' in session:
        return await flash('error', 'Please login first.', 'login')
    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author = Privileges(int(author['priv']))
    if Privileges.Admin not in author:
        return await flash('error', f'You have insufficient privileges. If you have privileges, try entering your profile to reload them.', 'home')

    users_nobadge = await glob.db.fetchall(
        "SELECT u.id, u.name, u.country, u.email, u.discord_content, u.priv, "
        "i.ip, i.osu_stream, i.latest_datetime "
        "FROM users u "
        "JOIN ( "
        "  SELECT userid, ip, osu_stream, MAX(datetime) as latest_datetime "
        "  FROM ingame_logins "
        "  GROUP BY userid, ip, osu_stream "
        ") i ON u.id = i.userid AND i.latest_datetime = ( "
        "  SELECT MAX(datetime) FROM ingame_logins WHERE userid = i.userid "
        ") "
        "ORDER BY u.id DESC "
    )

    users = []

    for i in users_nobadge:
        group_list = []
        ipriv = Privileges(int(i['priv']))

        if Privileges.Normal not in ipriv:
            group_list.append(["Restricted", "#ff0000", "fa-ban"])
        else:
            if int(i['id']) in [3]:
                group_list.append(["Owner", "#e27030", "fa-cat"])
            elif Privileges.Admin in ipriv:
                group_list.append(["ADM", "#fbc531", ""])
            elif Privileges.Mod in ipriv:
                group_list.append(["GMT", "#28a40c", ""])
            if Privileges.Dangerous in ipriv:
                group_list.append(["Developer", "#515981", "fa-code"])
            if Privileges.Nominator in ipriv:
                group_list.append(["BN", "#30E2BF", "fa-music"])
            if Privileges.Alumni in ipriv:
                group_list.append(["Alumni", "#ea8685", "fa-door-open"])
            if Privileges.Oguser in ipriv:
                group_list.append(["OG", "#e88d15", "fa-frog"])
            elif Privileges.Normal in ipriv:
                group_list.append(["Normal", "#FFFFFF", "fa-circle-user"])
            if Privileges.Supporter in ipriv:
                if Privileges.Premium not in ipriv:
                    group_list.append(["Supporter", "#f78fb3", "fa-heart"])
                else:
                    group_list.append(["Supporter", "#f78fb3", "fa-fire"])
            if Privileges.Whitelisted in ipriv:
                i['priv'] = "Verified"

        user = i.copy()
        user['group_list'] = group_list

        users.append(user)

    # fetch data from database
    user_data = await glob.db.fetch(
        'SELECT COUNT(id) registered, '
        '(SELECT COUNT(id) FROM users WHERE NOT priv & 1) banned, '
        '(SELECT COUNT(id) FROM users WHERE priv & 16 OR priv & 32) supporter '
        'FROM users'
    )

    # fetch data from database
    dash_data = await glob.db.fetch(
        'SELECT COUNT(id) count, '
        '(SELECT name FROM users ORDER BY id DESC LIMIT 1) lastest_user, '
        '(SELECT COUNT(id) FROM users WHERE NOT priv & 1) banned '
        'FROM users'
    )

    recent_users = await glob.db.fetchall('SELECT * FROM users ORDER BY id DESC LIMIT 5')
    recent_scores = await glob.db.fetchall(
        'SELECT scores.*, maps.artist, maps.title, '
        'maps.set_id, maps.creator, maps.version '
        'FROM scores JOIN maps ON scores.map_md5 = maps.md5 '
        'ORDER BY scores.id DESC LIMIT 5'
    )

    admin_data = await glob.db.fetch(
        'SELECT id, safe_name, name, priv '
        'FROM users '
        'WHERE %s ',
        [session['user_data']['id']]
    )

    score_count = await glob.db.fetch('SELECT MAX(id) AS max_id FROM scores')

    supporter_count = await glob.db.fetch(
        'SELECT id, name, donor_end, '
        '(SELECT COUNT(*) FROM users WHERE donor_end <> 0) AS donor_count '
        'FROM users '
        'WHERE donor_end <> 0 '
    )
    
    async with glob.http.get("https://api.komako.pw/get_player_count") as r:
        resp = await r.json()
    user_data['online'] = resp['counts']['online']

    return await render_template('admin/users.html', users=users, user_data=user_data, dashdata=dash_data, 
                                 recentusers=recent_users, recentscores=recent_scores, admin_data=admin_data,
                                 score_count=score_count, supporter_count=supporter_count)

@admin.route('/users/edit/<id>')
async def user_edit(id):
    """Edit User Page."""

    if not 'authenticated' in session:
        return await flash('error', 'Please login first.', 'login')
    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author = Privileges(int(author['priv']))
    if Privileges.Admin not in author:
        return await flash('error', f'You have insufficient privileges. If you have privileges, try entering your profile to reload them.', 'home')

    user_data = await glob.db.fetch(
        'SELECT id, name, email, priv, country, silence_end, donor_end, '
        'creation_time, latest_activity, clan_id, clan_priv, '
        'discord_content, occupation_content, location_content, interest_content '
        'FROM users '
        'WHERE safe_name IN (%s) OR id IN (%s) LIMIT 1',
        [id, get_safe_name(id)]
    )

    logs_data = await glob.db.fetchall(
        'SELECT l.id, u1.name AS from_name, l.`from`, u2.name AS to_name, l.`to`, l.action, l.msg, l.`time` '
        'FROM logs AS l '
        'JOIN users AS u1 ON l.`from` = u1.id '
        'JOIN users AS u2 ON l.`to` = u2.id '
        'WHERE l.`to` IN (%s) '
        'ORDER BY l.`time` DESC',
        [id]
    )

    #get offline/online status
    # Inside your route function
    user_id = user_data['id']

    # Get offline/online status
    check_status = requests.get(f'http://bancho/v1/get_player_status?id={user_id}', headers={'Host': 'api.meow.nya'})
    if check_status.status_code == 200:
        status_data = check_status.json()
        player_status = status_data.get("player_status", {})
        online_status = player_status.get("online", False)
    else:
        # Handle API error or invalid response
        online_status = False  # Assume user is offline in case of error

    #Permission checks
    usrprv = Privileges(int(user_data['priv']))
    admpriv = Privileges(int(session['user_data']['priv']))
    #Editing admin (Dev, owners only)
    #Editing owner (Owners only)
    if int(user_data['id']) in [3,4] and int(session['user_data']['id']) not in [3,4]:
        access_denied = {'higher_group': True, 'err_msg': "You dont have permissions to edit Owners"}
        return await render_template('admin/edit_user.html', user_data=user_data, access_denied=access_denied)
    else:
        access_denied = {'higher_group': False}
    #Editing dev (Owners only)
    if Privileges.Dangerous in usrprv and int(session['user_data']['id']) not in [3,4]:
        access_denied = {'higher_group': True, 'err_msg': "You dont have permissions to edit Developers"}
        return await render_template('admin/edit_user.html', user_data=user_data, access_denied=access_denied)
    else:
        access_denied = {'higher_group': False}
    if Privileges.Admin in usrprv and Privileges.Dangerous not in admpriv:
        access_denied = {'higher_group': True, 'err_msg': "You dont have permissions to edit Admins"}
        return await render_template('admin/edit_user.html', user_data=user_data, access_denied=access_denied)
    else:
        access_denied = {'higher_group': False}


    #Format join date
    user_data['creation_time'] = datetime.datetime.fromtimestamp(int(user_data['creation_time'])).strftime("%d %B %Y, %H:%M")

    admin = session['user_data']
    if int(admin['id']) in [3,4]:
        admin['is_owner'] = True

    return await render_template('admin/edit_user.html', user_data=user_data, logs_data=logs_data, admin=admin, access_denied=access_denied,
                                 online_status=online_status)

from quart import redirect, flash

@admin.route('/users/wipe_socials/<id>', methods=['POST'])
async def wipe_socials(id):
    """Wipe user social information."""
    
    # Ensure user is authenticated and has sufficient privileges
    if not 'authenticated' in session:
        flash('error', 'Please login first.', 'login')
        return redirect(url_for('auth.login'))  # Adjust the login route as per your application

    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author = Privileges(int(author['priv']))
    
    if Privileges.Admin not in author:
        flash('error', 'You have insufficient privileges. If you have privileges, try entering your profile to reload them.', 'home')
        return redirect(url_for('home'))  # Adjust the home route as per your application

    # Check if the user to be edited exists
    user_data = await glob.db.fetch('SELECT id, priv FROM users WHERE id=%s', id)
    if not user_data:
        flash('error', 'User not found.', 'home')
        return redirect(url_for('home'))  # Adjust the home route as per your application

    usrprv = Privileges(int(user_data['priv']))
    admpriv = Privileges(int(session['user_data']['priv']))

    # Check permissions to edit user
    if int(user_data['id']) in [3, 4] and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Owners", 'admin_edit_user')
        return redirect(url_for('admin_edit_user'))  # Adjust the admin_edit_user route as per your application
    if Privileges.Dangerous in usrprv and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Developers", 'admin_edit_user')
        return redirect(url_for('admin_edit_user'))  # Adjust the admin_edit_user route as per your application
    if Privileges.Admin in usrprv and Privileges.Dangerous not in admpriv:
        flash('error', "You don't have permissions to edit Admins", 'admin_edit_user')
        return redirect(url_for('admin_edit_user'))  # Adjust the admin_edit_user route as per your application

    # Perform the update
    await glob.db.execute(
        'UPDATE users SET discord_content = NULL, occupation_content = NULL, location_content = NULL, interest_content = NULL WHERE id = %s',
        [id]
    )

    # Redirect to the user edit page
    return redirect(url_for('admin.user_edit', id=id))

@admin.route('/invite')
async def invitegen():
    if not glob.config.keys:
        return await flash('error', 'The use of keys is currently disabled/unneeded!', 'home')

    if not 'authenticated' in session:
        return await flash('error', 'You must be logged in to access the key gen!', 'login')

    if not session["user_data"]["is_oguser"] and not session["user_data"]["is_staff"]:
        return await flash('error', 'You must be a donator/staff member to do this!', 'settings/profile')

    return await render_template('admin/invite.html')

@admin.route('/edit_map')
async def edit_map():
    if not 'authenticated' in session and not session["user_data"]["is_staff"]:
        return await flash('error', 'You cannot be here!', 'login')
    
    return await render_template('admin/edit_map.html')

@admin.route('/invite', methods=['POST'])
async def gen_invite():
    if glob.config.keys:
        if session["user_data"]["is_staff"]:
                e = await glob.db.fetch(f'SELECT keygen FROM users WHERE id = {session["user_data"]["id"]}')
                if not e['keygen'] > 0 or session["user_data"]["is_staff"]:
                    key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
                    await glob.db.execute('INSERT INTO beta_keys(beta_key, generated_by) VALUES (%s, %s)', [key, session["user_data"]["name"]])
                    await glob.db.execute('UPDATE users SET keygen = keygen + 1 WHERE id = %s', [session["user_data"]["id"]])
                    return await render_template('admin/invite.html', keygen=key)
                else:
                    return await flash('error', 'You have already generated a key!', 'key')
        else:
            return await flash('error', 'You do not have permissions to do this!', 'key')
    else:
        return await flash('error', 'The use of keys is currently disabled/unneeded!', 'home')
    
@admin.route('/news')
async def news():
    if not 'authenticated' in session:
        return await flash('error', 'Please login first.', 'login')

    if not session['user_data']['is_staff']:
        return await flash('error', f'You have insufficient privileges.', 'home')
    
    # create some kind of query for existing news post to display previous posts on the page

    return await render_template('admin/news.html')

@admin.route('/news', methods=['POST'])
async def post_news():
    if not 'authenticated' in session:
        return await flash('error', 'Please login first.', 'login')

    if not session['user_data']['is_staff']:
        return await flash('error', f'You have insufficient privileges.', 'home')

    form = await request.form
    icon = form['icon']
    title = form['title']
    content = form['content']
    posted_by = session['user_data']['id']
    poster_name = session['user_data']['name']
    date_posted = time.strftime('%Y-%m-%d %H:%M:%S')

    await glob.db.execute(
        'INSERT INTO news (icon, title, content, posted_by, poster_name, date_posted) VALUES (%s, %s, %s, %s, %s, %s)',
        [icon, title, content, posted_by, poster_name, date_posted]
    )

    return await flash('success', 'News post has been successfully posted!', 'admin/news')

@admin.route('/edithome')
async def edithome():
    if not 'authenticated' in session:
        return await flash('error', 'Please login first.', 'login')

    if not session['user_data']['is_staff']:
        return await flash('error', f'You have insufficient privileges.', 'home')
    
    misc_data = await glob.db.fetch('SELECT * FROM misc')

    return await render_template('admin/homepage.html', misc_data=misc_data)

@admin.route('/edithome', methods=['POST'])
async def post_homepage():
    if not 'authenticated' in session:
        return await flash('error', 'Please login first.', 'login')

    if not session['user_data']['is_staff']:
        return await flash('error', f'You have insufficient privileges.', 'home')

    form = await request.form
    videourl = form['videourl']

    await glob.db.execute(
        'UPDATE misc SET home_video = %s',
        [videourl]
    )

    return await flash('success', 'Homepage has been successfully updated!', 'admin/homepage')