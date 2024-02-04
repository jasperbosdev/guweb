# -*- coding: utf-8 -*-

__all__ = ()

import datetime

import json
import string
import random
import timeago
import requests
from quart import Blueprint
from quart import render_template
from quart import session
from quart import request

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
        'admin/home.html', dashdata=dash_data,
        recentusers=recent_users, recentscores=recent_scores,
        datetime=datetime, timeago=timeago, admin_data=admin_data,
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
        'creation_time, latest_activity, clan_id, clan_priv '
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


    return await render_template('admin/edit_user.html', user_data=user_data, logs_data=logs_data, admin=admin, access_denied=access_denied
                                 , online_status=online_status)

@admin.route('/invite')
async def invitegen():
    if not glob.config.keys:
        return await flash('error', 'The use of keys is currently disabled/unneeded!', 'home')

    if not 'authenticated' in session:
        return await flash('error', 'You must be logged in to access the key gen!', 'login')

    if not session["user_data"]["is_oguser"] and not session["user_data"]["is_staff"]:
        return await flash('error', 'You must be a donator/staff member to do this!', 'settings/profile')

    return await render_template('admin/invite.html')

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