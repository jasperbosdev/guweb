# -*- coding: utf-8 -*-

__all__ = ()

import datetime

import os
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
from pathlib import Path
from PIL import Image

from objects import glob
from objects.utils import flash
from objects.privileges import Privileges
from objects.utils import get_safe_name

admin = Blueprint('admin', __name__)

PRIV_UNRESTRICTED = 1
PRIV_VERIFIED = 2
PRIV_WHITELISTED = 4
PRIV_SUPPORTER = 16
PRIV_PREMIUM = 32
PRIV_ALUMNI = 128
PRIV_OGUSER = 33554432
PRIV_TOURNEY_MANAGER = 1024
PRIV_NOMINATOR = 2048
PRIV_MODERATOR = 4096
PRIV_ADMINISTRATOR = 8192
PRIV_DEVELOPER = 16384
PRIV_DONATOR = PRIV_SUPPORTER | PRIV_PREMIUM
PRIV_STAFF = PRIV_MODERATOR | PRIV_ADMINISTRATOR | PRIV_DEVELOPER

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
        'SELECT id, name, safe_name, username_aka, email, priv, country, silence_end, donor_end, '
        'creation_time, latest_activity, clan_id, clan_priv, private_mode, '
        'discord_content, occupation_content, location_content, interest_content, '
        'userpage_content, is_legit '
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

    current_time = int(time.time())

    return await render_template('admin/edit_user.html', user_data=user_data, logs_data=logs_data, admin=admin, access_denied=access_denied,
                                 online_status=online_status, current_time=current_time)

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
    
    misc_data = await glob.db.fetch('SELECT home_video FROM misc')
    
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

ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png', '.gif']
BANNERS_PATH = Path.cwd() / '.data/banners'
DEFAULT_BANNER_PATH = 'static/images/default.jpg'

@admin.route('/users/clear_banner/<id>', methods=['POST'])
async def clear_banner(id):
    """Clear user's banner and set to default."""
    
    if not 'authenticated' in session:
        flash('error', 'Please login first.')
        return redirect(url_for('auth.login'))  # Adjust the login route as per your application
    
    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author_privileges = Privileges(int(author['priv']))

    if Privileges.Admin not in author_privileges:
        flash('error', 'You have insufficient privileges.')
        return redirect(url_for('home'))  # Adjust the home route as per your application
    
    # Check if the user to be edited exists
    user_data = await glob.db.fetch('SELECT id, priv FROM users WHERE id=%s', id)
    if not user_data:
        flash('error', 'User not found.')
        return redirect(url_for('home'))  # Adjust the home route as per your application
    
    usrprv = Privileges(int(user_data['priv']))
    admpriv = Privileges(int(session['user_data']['priv']))
    
    # Check permissions to edit user
    if int(user_data['id']) in [3, 4] and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Owners.")
        return redirect(url_for('admin.user_edit', id=id))  # Adjust the admin_edit_user route as per your application
    if Privileges.Dangerous in usrprv and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Developers.")
        return redirect(url_for('admin.user_edit', id=id))  # Adjust the admin_edit_user route as per your application
    if Privileges.Admin in usrprv and Privileges.Dangerous not in admpriv:
        flash('error', "You don't have permissions to edit Admins.")
        return redirect(url_for('admin.user_edit', id=id))  # Adjust the admin_edit_user route as per your application
    
    # Remove the current banner if it exists
    for ext in ALLOWED_EXTENSIONS:
        banner_path = BANNERS_PATH / f'{id}{ext}'
        if banner_path.exists():
            banner_path.unlink()

    # Flash success message
    flash('success', 'User banner cleared successfully.', '')

    # Redirect to the user edit page
    return redirect(url_for('admin.user_edit', id=id))

ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png', '.gif']
BACKGROUND_PATH = Path.cwd() / '.data/backgrounds'

@admin.route('/users/clear_background/<id>', methods=['POST'])
async def clear_background(id):
    """Clear user's background."""
    
    if not 'authenticated' in session:
        flash('error', 'Please login first.')
        return redirect(url_for('auth.login'))  # Adjust the login route as per your application
    
    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author_privileges = Privileges(int(author['priv']))

    if Privileges.Admin not in author_privileges:
        flash('error', 'You have insufficient privileges.')
        return redirect(url_for('home'))  # Adjust the home route as per your application
    
    # Check if the user to be edited exists
    user_data = await glob.db.fetch('SELECT id, priv FROM users WHERE id=%s', id)
    if not user_data:
        flash('error', 'User not found.')
        return redirect(url_for('home'))  # Adjust the home route as per your application
    
    usrprv = Privileges(int(user_data['priv']))
    admpriv = Privileges(int(session['user_data']['priv']))
    
    # Check permissions to edit user
    if int(user_data['id']) in [3, 4] and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Owners.")
        return redirect(url_for('admin.user_edit', id=id))  # Adjust the admin_edit_user route as per your application
    if Privileges.Dangerous in usrprv and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Developers.")
        return redirect(url_for('admin.user_edit', id=id))  # Adjust the admin_edit_user route as per your application
    if Privileges.Admin in usrprv and Privileges.Dangerous not in admpriv:
        flash('error', "You don't have permissions to edit Admins.")
        return redirect(url_for('admin.user_edit', id=id))  # Adjust the admin_edit_user route as per your application
    
    # Remove the current background if it exists
    for ext in ALLOWED_EXTENSIONS:
        background_path = BACKGROUND_PATH / f'{id}{ext}'
        if background_path.exists():
            background_path.unlink()

    # Flash success message
    flash('success', 'User banner cleared successfully.', '')

    # Redirect to the user edit page
    return redirect(url_for('admin.user_edit', id=id))

ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png', '.gif']
AVATARS_PATH = Path(f'{glob.config.path_to_gulag}.data/avatars')

@admin.route('/users/clear_avatar/<id>', methods=['POST'])
async def clear_avatar(id):
    """Clear user's avatar."""
    
    if not 'authenticated' in session:
        flash('error', 'Please login first.')
        return redirect(url_for('auth.login'))  # Adjust the login route as per your application
    
    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author_privileges = Privileges(int(author['priv']))

    if Privileges.Admin not in author_privileges:
        flash('error', 'You have insufficient privileges.')
        return redirect(url_for('home'))  # Adjust the home route as per your application
    
    # Check if the user to be edited exists
    user_data = await glob.db.fetch('SELECT id, priv FROM users WHERE id=%s', id)
    if not user_data:
        flash('error', 'User not found.')
        return redirect(url_for('home'))  # Adjust the home route as per your application
    
    usrprv = Privileges(int(user_data['priv']))
    admpriv = Privileges(int(session['user_data']['priv']))
    
    # Check permissions to edit user
    if int(user_data['id']) in [3, 4] and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Owners.")
        return redirect(url_for('admin.user_edit', id=id))  # Adjust the admin_edit_user route as per your application
    if Privileges.Dangerous in usrprv and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Developers.")
        return redirect(url_for('admin.user_edit', id=id))  # Adjust the admin_edit_user route as per your application
    if Privileges.Admin in usrprv and Privileges.Dangerous not in admpriv:
        flash('error', "You don't have permissions to edit Admins.")
        return redirect(url_for('admin.user_edit', id=id))  # Adjust the admin_edit_user route as per your application
    
    # Remove the current avatar if it exists
    for ext in ALLOWED_EXTENSIONS:
        avatar_path = AVATARS_PATH / f'{id}{ext}'
        if avatar_path.exists():
            avatar_path.unlink()

    # Flash success message
    flash('success', 'User avatar cleared successfully.', '')

    # Redirect to the user edit page
    return redirect(url_for('admin.user_edit', id=id))

@admin.route('/users/clear_aboutme/<id>', methods=['POST'])
async def clear_aboutme(id):
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
        'UPDATE users SET userpage_content = NULL WHERE id = %s',
        [id]
    )

    # Redirect to the user edit page
    return redirect(url_for('admin.user_edit', id=id))

@admin.route('/admin/users/update_userinfo/<int:id>', methods=['POST'])
async def update_userinfo(id):
    # Ensure user is authenticated and has sufficient privileges
    if 'authenticated' not in session:
        flash('error', 'Please login first.', 'login')
        return redirect(url_for('auth.login'))  # Adjust the login route as per your application

    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author = Privileges(int(author['priv']))
    
    if Privileges.Admin not in author:
        flash('error', 'You have insufficient privileges. If you have privileges, try entering your profile to reload them.', 'home')
        return redirect(url_for('home'))  # Adjust the home route as per your application

    # Check if the user to be edited exists
    user_data = await glob.db.fetch(
        'SELECT id, name, safe_name, email, priv, username_aka, country, silence_end, donor_end, '
        'creation_time, latest_activity, clan_id, clan_priv, '
        'discord_content, occupation_content, location_content, interest_content, '
        'userpage_content '
        'FROM users '
        'WHERE id = %s LIMIT 1',
        [id]
    )

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

    form = await request.form

    # Extract form data
    new_name = form.get('username', '').strip()
    new_safe_name = form.get('safename', '').strip()
    new_email = form.get('email', '').strip()
    new_username_aka = form.get('username_aka', '').strip()
    new_country = form.get('country', '').strip()  # Assuming country is updated via a select box

    # Check if "Set Default" or "Clear" action is triggered
    if 'set_default_aka' in form:
        new_username_aka = None  # Set to None to update to NULL in database

    if 'clear_aka' in form:
        new_username_aka = ''  # Set to empty string to clear, adjust as needed

    # Determine changes
    changes = {}

    if new_name and new_name != user_data['name']:
        changes['name'] = new_name

    if new_safe_name and new_safe_name != user_data['safe_name']:
        changes['safe_name'] = new_safe_name

    if new_email and new_email != user_data['email']:
        changes['email'] = new_email

    if new_username_aka is not None and new_username_aka != user_data['username_aka']:
        changes['username_aka'] = new_username_aka

    if new_country and new_country != user_data['country']:
        changes['country'] = new_country

    # Update database if changes are detected
    if changes:
        set_clauses = []
        params = []

        for key, value in changes.items():
            if value is None:
                set_clauses.append(f'{key} = NULL')
            else:
                set_clauses.append(f'{key} = %s')
                params.append(value)

        params.append(id)  # Append user ID to the parameter list

        await glob.db.execute(
            f'UPDATE users SET {", ".join(set_clauses)} WHERE id = %s',
            params
        )

        flash('success', 'User information updated successfully.', 'admin_edit_user')
    else:
        flash('info', 'No changes detected.', 'admin_edit_user')

    return redirect(url_for('admin.user_edit', id=id))  # Adjust as per your application

@admin.route('/admin/users/private_profile/<int:id>', methods=['POST'])
async def private_profile(id):
    # Ensure user is authenticated and has sufficient privileges
    if 'authenticated' not in session:
        flash('error', 'Please login first.', 'login')
        return redirect(url_for('auth.login'))

    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author = Privileges(int(author['priv']))
    
    if Privileges.Admin not in author:
        flash('error', 'You have insufficient privileges.', 'home')
        return redirect(url_for('home'))

    # Check if the user to be edited exists
    user_data = await glob.db.fetch('SELECT id, priv, private_mode FROM users WHERE id=%s', id)
    if not user_data:
        flash('error', 'User not found.', 'home')
        return redirect(url_for('home'))

    usrprv = Privileges(int(user_data['priv']))
    admpriv = Privileges(int(session['user_data']['priv']))

    # Check permissions to edit user
    if int(user_data['id']) in [3, 4] and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Owners", 'admin_edit_user')
        return redirect(url_for('admin_edit_user'))
    if Privileges.Dangerous in usrprv and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Developers", 'admin_edit_user')
        return redirect(url_for('admin_edit_user'))
    if Privileges.Admin in usrprv and Privileges.Dangerous not in admpriv:
        flash('error', "You don't have permissions to edit Admins", 'admin_edit_user')
        return redirect(url_for('admin_edit_user'))
    
    # Toggle private mode
    new_private_mode = 1 if user_data['private_mode'] == 0 else 0

    await glob.db.execute(
        'UPDATE users SET private_mode = %s WHERE id = %s',
        [new_private_mode, id]
    )

    flash('success', 'Profile privacy updated successfully.', 'admin_edit_user')
    return redirect(url_for('admin.user_edit', id=id))

@admin.route('/admin/users/clear_graphs/<id>', methods=['POST'])
async def clear_graphs(id):
    """Clear user's graphs."""

    # Ensure user is authenticated and has sufficient privileges
    if 'authenticated' not in session:
        flash('error', 'Please login first.', 'login')
        return redirect(url_for('auth.login'))

    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author = Privileges(int(author['priv']))
    
    if Privileges.Admin not in author:
        flash('error', 'You have insufficient privileges.', 'home')
        return redirect(url_for('home'))

    # Check if the user to be edited exists
    user_data = await glob.db.fetch('SELECT id, priv, private_mode FROM users WHERE id=%s', id)
    if not user_data:
        flash('error', 'User not found.', 'home')
        return redirect(url_for('home'))

    usrprv = Privileges(int(user_data['priv']))
    admpriv = Privileges(int(session['user_data']['priv']))

    # Check permissions to edit user
    if int(user_data['id']) in [3, 4] and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Owners", 'admin_edit_user')
        return redirect(url_for('admin_edit_user'))
    if Privileges.Dangerous in usrprv and int(session['user_data']['id']) not in [3, 4]:
        flash('error', "You don't have permissions to edit Developers", 'admin_edit_user')
        return redirect(url_for('admin_edit_user'))
    if Privileges.Admin in usrprv and Privileges.Dangerous not in admpriv:
        flash('error', "You don't have permissions to edit Admins", 'admin_edit_user')
        return redirect(url_for('admin_edit_user'))
    
    # Perform the function
    print(f"Deleting user history for user id: {id}")
    await glob.db.execute(
        'DELETE FROM user_history WHERE id = %s',
        [id]
    )

    # Flash success message
    flash('success', 'User graphs cleared successfully.', '')

    # Redirect to the user edit page
    return redirect(url_for('admin.user_edit', id=id))

@admin.route('/admin/users/restrict/<id>', methods=['POST'])
async def restrict_user(id):
    """Restrict a user by updating their priv value to 2 (restricted state)."""

    form_data = await request.form
    reason = form_data.get('reason')

    # Ensure user is authenticated and has sufficient privileges
    if 'authenticated' not in session:
        flash('error', 'Please login first.', 'login')
        return redirect(url_for('auth.login'))

    # Fetch the author's privileges from the session
    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author_priv = int(author['priv'])

    # Check if the user has the ADMINISTRATOR privilege
    if author_priv & PRIV_ADMINISTRATOR == 0:
        flash('error', 'You have insufficient privileges.', 'home')
        return redirect(url_for('home'))

    # Check if the user to be restricted exists
    user_data = await glob.db.fetch('SELECT id, priv, priv_og FROM users WHERE id=%s', id)
    if not user_data:
        flash('error', 'User not found.', 'home')
        return redirect(url_for('home'))

    # Save the original privileges before restricting
    original_priv = user_data['priv']
    if user_data['priv_og'] is None:  # Only update if priv_og is not already set
        await glob.db.execute(
            'UPDATE users SET priv = %s, priv_og = %s WHERE id = %s',
            [2, original_priv, id]
        )
    else:
        await glob.db.execute(
            'UPDATE users SET priv = %s WHERE id = %s',
            [2, id]
        )

    # Log the action
    await glob.db.execute(
        "INSERT INTO logs (`from`, `to`, `action`, `msg`, `time`) "
        "VALUES (%s, %s, %s, %s, NOW())",
        [session['user_data']['id'], id, 'restrict', reason]
    )

    # Provide feedback
    flash('success', 'User has been restricted successfully.', '')

    # Redirect to the user edit page or admin dashboard
    return redirect(url_for('admin.user_edit', id=id))

@admin.route('/admin/users/unrestrict/<id>', methods=['POST'])
async def unrestrict_user(id):
    """Unrestrict a user by restoring their original priv value."""

    form_data = await request.form
    reason = form_data.get('reason')

    # Ensure user is authenticated and has sufficient privileges
    if 'authenticated' not in session:
        flash('error', 'Please login first.', 'login')
        return redirect(url_for('auth.login'))

    # Fetch the author's privileges from the session
    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author_priv = int(author['priv'])

    # Check if the user has the ADMINISTRATOR privilege
    if author_priv & PRIV_ADMINISTRATOR == 0:
        flash('error', 'You have insufficient privileges.', 'home')
        return redirect(url_for('home'))

    # Check if the user to be unrestricted exists
    user_data = await glob.db.fetch('SELECT id, priv, priv_og FROM users WHERE id=%s', id)
    if not user_data:
        flash('error', 'User not found.', 'home')
        return redirect(url_for('home'))

    # Restore original privileges
    original_priv = user_data['priv_og']
    if original_priv is not None:
        await glob.db.execute(
            'UPDATE users SET priv = %s, priv_og = NULL WHERE id = %s',
            [original_priv, id]
        )

        # Log the action
        await glob.db.execute(
            "INSERT INTO logs (`from`, `to`, `action`, `msg`, `time`) "
            "VALUES (%s, %s, %s, %s, NOW())",
            [session['user_data']['id'], id, 'unrestrict', reason]
        )

        # Provide feedback
        flash('success', 'User has been unrestricted successfully.', '')

    else:
        flash('error', 'Original privileges not found.', '')

    # Redirect to the user edit page or admin dashboard
    return redirect(url_for('admin.user_edit', id=id))

@admin.route('/admin/users/wipe_account/<id>', methods=['POST'])
async def wipe_account(id):
    """Wipe a user's account by clearing their data."""

    form_data = await request.form
    reason = form_data.get('reason')

    # Ensure user is authenticated and has sufficient privileges
    if 'authenticated' not in session:
        flash('error', 'Please login first.', 'login')
        return redirect(url_for('auth.login'))

    # Fetch the author's privileges from the session
    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author_priv = int(author['priv'])

    # Check if the user has the ADMINISTRATOR privilege
    if author_priv & PRIV_ADMINISTRATOR == 0:
        flash('error', 'You have insufficient privileges.', 'home')
        return redirect(url_for('home'))

    # Check if the user to be wiped exists
    user_data = await glob.db.fetch('SELECT id, priv, priv_og FROM users WHERE id=%s', id)
    if not user_data:
        flash('error', 'User not found.', 'home')
        return redirect(url_for('home'))
    
    #Perform the wipe, wipe all scores from this user
    await glob.db.execute(
        'DELETE FROM scores where userid = %s',
        [id]
    )

    #Reset the user's stats
    await glob.db.execute(
        'UPDATE stats SET tscore = 0, rscore = 0, pp = 0, plays = 0, playtime = 0, acc = 0, max_combo = 0, total_hits = 0, '
        'replay_views = 0, xh_count = 0, x_count = 0, sh_count = 0, s_count = 0, a_count = 0 '
        'WHERE id = %s',
        [id]
    )

    # Log the action
    await glob.db.execute(
        "INSERT INTO logs (`from`, `to`, `action`, `msg`, `time`) "
        "VALUES (%s, %s, %s, %s, NOW())",
        [session['user_data']['id'], id, 'wipe', reason]
    )

    # Provide feedback
    flash('success', 'User has been wiped successfully.', '')

    return redirect(url_for('admin.user_edit', id=id))

@admin.route('/admin/users/verified_user/<id>', methods=['POST'])
async def verified_user(id):
    """Verify a user for being a legit player."""

    # Ensure user is authenticated and has sufficient privileges
    if 'authenticated' not in session:
        flash('error', 'Please login first.', 'login')
        return redirect(url_for('auth.login'))

    # Fetch the author's privileges from the session
    author = await glob.db.fetch("SELECT priv FROM users WHERE id=%s", session['user_data']['id'])
    session['user_data']['priv'] = author['priv']
    author_priv = int(author['priv'])

    # Check if the user has the ADMINISTRATOR privilege
    if author_priv & PRIV_ADMINISTRATOR == 0:
        flash('error', 'You have insufficient privileges.', 'home')
        return redirect(url_for('home'))

    # Check if the user to be verified exists
    user_data = await glob.db.fetch('SELECT id, is_legit FROM users WHERE id=%s', [id])
    if not user_data:
        flash('error', 'User not found.', 'home')
        return redirect(url_for('home'))  

    #Check if already verified to unverify if the case
    new_legit = 1 if user_data['is_legit'] == 0 else 0

    #Perform the verification
    await glob.db.execute(
        'UPDATE users SET is_legit = %s WHERE id = %s',
        [new_legit, id]
    )

    # Provide feedback
    flash('success', 'User has been verified successfully.', '')

    return redirect(url_for('admin.user_edit', id=id))