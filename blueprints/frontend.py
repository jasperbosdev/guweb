    # -*- coding: utf-8 -*-

__all__ = ()

import bcrypt
import hashlib
import os
import string
import time
import timeago
import asyncio
import json
import requests
import datetime

from cmyui.logging import Ansi
from cmyui.logging import log
from cmyui.osu import Mods
from functools import wraps
from PIL import Image
from pathlib import Path
from quart import Blueprint
from quart import redirect
from quart import render_template
from quart import request
from quart import session
from quart import send_file
from quart import redirect, url_for
from datetime import datetime

from constants import regexes
from objects import glob
from objects import utils
from objects.privileges import Privileges
from objects.utils import flash
from objects.utils import flash_with_customizations

VALID_MODES = frozenset({'std', 'taiko', 'catch', 'mania'})
VALID_MODS = frozenset({'vn', 'rx', 'ap'})

frontend = Blueprint('frontend', __name__)

#code to calculate levels
def get_required_score_for_level(level: int) -> float:
    if level <= 100:
        if level >= 2:
            return 5000 / 3 * (4 * (level ** 3) - 3 * (level ** 2) - level) + 1.25 * (1.8 ** (level - 60))
        else:
            return 1.0  # Should be 0, but we get division by 0 below so set to 1
    else:
        return 26931190829 + 1e11 * (level - 100)

def get_level(total_score: int) -> int:
    level = 1
    while True:
        # Avoid endless loops
        if level > 120:
            return level

        # Calculate required score
        reqScore = get_required_score_for_level(level)

        # Check if this is our level
        if total_score <= reqScore:
            # Our level, return it and break
            return level - 1
        else:
            # Not our level, calculate score for next level
            level += 1

# bbcode
import re
from markupsafe import escape
def bbcode(value):
    bbdata = [
        (r'\[url\](.+?)\[/url\]', r'<a href="\1">\1</a>'),
        (r'\[url=(.+?)\](.+?)\[/url\]', r'<a href="\1">\2</a>'),
        (r'\[email\](.+?)\[/email\]', r'<a href="mailto:\1">\1</a>'),
        (r'\[email=(.+?)\](.+?)\[/email\]', r'<a href="mailto:\1">\2</a>'),
        (r'\[img\](.+?)\[/img\]', r'<img src="\1">'),
        (r'\[img=(.+?)\](.+?)\[/img\]', r'<img src="\1" alt="\2">'),
        (r'\[b\](.+?)\[/b\]', r'<b>\1</b>'),
        (r'\[i\](.+?)\[/i\]', r'<i>\1</i>'),
        (r'\[u\](.+?)\[/u\]', r'<u>\1</u>'),
        (r'\[quote\](.+?)\[/quote\]', r'<div style="margin-left: 1cm">\1</div>'),
        (r'\[center\](.+?)\[/center\]', r'<div align="center">\1</div>'),
        (r'\[code\](.+?)\[/code\]', r'<tt>\1</tt>'),
        (r'\[big\](.+?)\[/big\]', r'<big>\1</big>'),
        (r'\[small\](.+?)\[/small\]', r'<small>\1</small>'),
        (r'\[box=(.+?)\](.+?)\[/box\]', r'<div class="custom-spoilerbox" id="spoilerbox-\1"><a class="spoilerbox-link" href="#" onclick="toggleSpoilerBox(&quot;spoilerbox-\1&quot;)"><span class="spoilerbox-link-icon"></span>\1</a><div class="spoilerbox-content" style="display: none;">\2</div></div>'),
        (r'\[notice\](.*?)\[/notice\]', r'<div class="well">\1</div>')
    ]

    for bbset in bbdata:
        p = re.compile(bbset[0], re.DOTALL)
        value = p.sub(bbset[1], value)

    # Handling lists
    temp = ''
    p = re.compile(r'\[list\](.+?)\[/list\]', re.DOTALL)
    m = p.search(value)
    if m:
        items = re.split(re.escape('[*]'), m.group(1))
        for i in items[1:]:
            temp = temp + '<li>' + i + '</li>'
        value = p.sub(r'<ul>'+temp+'</ul>', value)

    temp = ''
    p = re.compile(r'\[list=(.)\](.+?)\[/list\]', re.DOTALL)
    m = p.search(value)
    if m:
        items = re.split(re.escape('[*]'), m.group(2))
        for i in items[1:]:
            temp = temp + '<li>' + i + '</li>'
        value = p.sub(r'<ol type=\1>'+temp+'</ol>', value)

    return value

def login_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not session:
            return await flash('error', 'You must be logged in to access that page.', 'login')
        return await func(*args, **kwargs)
    return wrapper

@frontend.route('/home')
@frontend.route('/')
async def home():

    pp_records = await glob.db.fetchall(
        '(SELECT scores.*, maps.*, scores.userid, users.priv, users.name, 0 as mode '
        'FROM scores '
        'JOIN maps ON scores.map_md5 = maps.md5 '
        'LEFT JOIN users ON scores.userid = users.id '
        'WHERE scores.mode = 0 AND users.priv <> 2 '
        'AND scores.status = 2 and maps.status = 2 ORDER BY scores.pp DESC LIMIT 1) '

        'UNION '

        '(SELECT scores.*, maps.*, scores.userid, users.priv, users.name, 4 as mode '
        'FROM scores '
        'JOIN maps ON scores.map_md5 = maps.md5 '
        'LEFT JOIN users ON scores.userid = users.id '
        'WHERE scores.mode = 4 AND users.priv <> 2 '
        'AND scores.status = 2 and maps.status = 2 ORDER BY scores.pp DESC LIMIT 1) '

        'UNION '

        '(SELECT scores.*, maps.*, scores.userid, users.priv, users.name, 8 as mode '
        'FROM scores '
        'JOIN maps ON scores.map_md5 = maps.md5 '
        'LEFT JOIN users ON scores.userid = users.id '
        'WHERE scores.mode = 8 AND users.priv <> 2 '
        'AND scores.status = 2 and maps.status = 2 ORDER BY scores.pp DESC LIMIT 1)'
    )

    for result in pp_records:
        result['mode_str'] = (
            'vn!std' if result['mode'] == 0 else
            'rx!std' if result['mode'] == 4 else
            'ap!std' if result['mode'] == 8 else ''
        )

    most_played = await glob.db.fetchall('SELECT * FROM maps ORDER BY maps.plays DESC LIMIT 3')
    recent_active = await glob.db.fetchall('SELECT * FROM users WHERE priv <> 2 and priv <> 1 ORDER BY latest_activity DESC LIMIT 4')

    recent_activity = await glob.db.fetchall(
        'SELECT sl.*, u.name, m.id AS map_id, m.title AS map_title, m.version, sniped_user.id AS sniper_id, m.mode '
        'FROM score_logs sl '
        'JOIN users u ON sl.user_id = u.id '
        'JOIN maps m ON sl.map_md5 = m.md5 '
        'LEFT JOIN users sniped_user ON sl.got_sniped_by = sniped_user.name '
        'ORDER BY sl.timestamp DESC LIMIT 10'
    )

    mode_strings = {
        0: "(osu!std)",
        4: "(osu!rx)",
        8: "(osu!ap)"
    }

    user_rank_1_maps = set()

    return await render_template('home.html', pp_records=pp_records, most_played=most_played, recent_active=recent_active,
                                 timeago=timeago, recent_activity=recent_activity, user_rank_1_maps=user_rank_1_maps, mode_strings=mode_strings)

@frontend.route('/home/account/edit')
async def home_account_edit():
    return redirect('/settings/profile')

@frontend.route('/settings/aboutme')
@frontend.route('/settings/about_me')
@login_required
async def settings_user_profile():
    about_me = await glob.db.fetch('SELECT userpage_content FROM users WHERE id=%s', session['user_data']['id'])
    if not about_me:
        about_me = {}
        about_me['userpage_content'] = ""

    return await render_template('settings/aboutme.html', about_me_content=about_me['userpage_content'])

@frontend.route('/settings/aboutme', methods=['POST'])
@login_required
async def settings_aboutme_post():
    form = await request.form

    new_about_me = form.get('about_me_content', type=str)
    old_about_me_row = await glob.db.fetch('SELECT userpage_content FROM users WHERE id=%s', session['user_data']['id'])
    old_about_me = old_about_me_row['userpage_content'] if old_about_me_row else ""


    if new_about_me == old_about_me or new_about_me is None or new_about_me == "":
        return await flash('error', 'No changes were made to the about me section.', 'settings/aboutme')

    if len(new_about_me) > 1500:
        return await flash('error', 'The about me content cannot exceed 1500 characters.', 'settings/aboutme')

    await glob.db.execute("UPDATE users SET userpage_content=%s WHERE id=%s", (new_about_me, session['user_data']['id']))

    return await flash('success', 'About me section updated successfully!', 'settings/aboutme')

@frontend.route('/settings')
@frontend.route('/settings/profile')
@login_required
async def settings_profile():
    return await render_template('settings/profile.html')


@frontend.route('/settings/profile', methods=['POST'])
@login_required
async def settings_profile_post():
    form = await request.form

    new_name = form.get('username', type=str)
    new_email = form.get('email', type=str)

    if new_name is None or new_email is None:
        return await flash('error', 'Invalid parameters.', 'home')

    old_name = session['user_data']['name']
    old_email = session['user_data']['email']

    if new_name != old_name:
        if not session['user_data']['is_donator']:
            return await flash('error', 'Username changes are currently a supporter perk.', 'settings/profile')

        # Usernames must:
        # - be within 2-15 characters in length
        # - not contain both ' ' and '_', one is fine
        # - not be in the config's `disallowed_names` list
        # - not already be taken by another player
        if not regexes.username.match(new_name):
            return await flash('error', 'Your new username syntax is invalid.', 'settings/profile')

        if '_' in new_name and ' ' in new_name:
            return await flash('error', 'Your new username may contain "_" or " ", but not both.', 'settings/profile')

        if new_name in glob.config.disallowed_names:
            return await flash('error', "Your new username isn't allowed; pick another.", 'settings/profile')

        if await glob.db.fetch('SELECT 1 FROM users WHERE name = %s', [new_name]):
            return await flash('error', 'Your new username already taken by another user.', 'settings/profile')

        safe_name = utils.get_safe_name(new_name)

        # username change successful
        await glob.db.execute(
            'UPDATE users '
            'SET name = %s, safe_name = %s '
            'WHERE id = %s',
            [new_name, safe_name, session['user_data']['id']]
        )

        # logout
        session.pop('authenticated', None)
        session.pop('user_data', None)
        return await flash('success', 'Your username/email have been changed! Please login again.', 'login')

    if new_email != old_email:
        # Emails must:
        # - match the regex `^[^@\s]{1,200}@[^@\s\.]{1,30}\.[^@\.\s]{1,24}$`
        # - not already be taken by another player
        if not regexes.email.match(new_email):
            return await flash('error', 'Your new email syntax is invalid.', 'settings/profile')

        if await glob.db.fetch('SELECT 1 FROM users WHERE email = %s', [new_email]):
            return await flash('error', 'Your new email already taken by another user.', 'settings/profile')

        # email change successful
        await glob.db.execute(
            'UPDATE users '
            'SET email = %s '
            'WHERE id = %s',
            [new_email, session['user_data']['id']]
        )

        # logout
        session.pop('authenticated', None)
        session.pop('user_data', None)
        return await flash('success', 'Your username/email have been changed! Please login again.', 'login')

    # occupation
    new_occupation = form.get('occupation_content', type=str)
    old_occupation = await glob.db.fetch('SELECT occupation_content FROM users WHERE id=%s', session['user_data']['id'])

    if new_occupation != old_occupation and new_occupation != None and new_occupation != "" and len(new_occupation) <= 50:
        await glob.db.execute("UPDATE users SET occupation_content=%s WHERE id=%s", (new_occupation, session['user_data']['id']))

    # location
    new_location = form.get('location_content', type=str)
    old_location = await glob.db.fetch('SELECT location_content FROM users WHERE id=%s', session['user_data']['id'])

    if new_location != old_location and new_location != None and new_location != "" and len(new_location) <= 50:
        await glob.db.execute("UPDATE users SET location_content=%s WHERE id=%s", (new_location, session['user_data']['id']))

    # interest
    new_interest = form.get('interest_content', type=str)
    old_interest = await glob.db.fetch('SELECT interest_content FROM users WHERE id=%s', session['user_data']['id'])

    if new_interest != old_interest and new_interest != None and new_interest != "" and len(new_interest) <= 50:
        await glob.db.execute("UPDATE users SET interest_content=%s WHERE id=%s", (new_interest, session['user_data']['id']))

    # playstyle
    updated_playstyle = False
    playstyle = 0

    if form.get('ps_tablet', type=str) == 'on':
        updated_playstyle = True
        playstyle = playstyle | 1
    if form.get('ps_mouse', type=str) == 'on':
        updated_playstyle = True
        playstyle = playstyle | 2
    if form.get('ps_keyboard', type=str) == 'on':
        updated_playstyle = True
        playstyle = playstyle | 4
    if form.get('ps_touch', type=str) == 'on':
        updated_playstyle = True
        playstyle = playstyle | 8

    if updated_playstyle:
        await glob.db.execute("UPDATE users SET play_style=%s WHERE id=%s", (playstyle, session['user_data']['id']))

    playstyle_value = playstyle  # This is the updated play_style value from the database

    # no data has changed; deny post
    if (
        new_name == old_name and
        new_email == old_email and
        new_occupation == old_occupation and
        new_location == old_location and
        new_interest == old_interest and
        not updated_playstyle
    ):
        return await flash('error', 'No changes have been made.', 'settings/profile')
    
    return await flash('success', 'Your profile has been successfully updated!', 'settings/profile')

@frontend.route('/settings/avatar')
@login_required
async def settings_avatar():
    return await render_template('settings/avatar.html')

@frontend.route('/settings/avatar', methods=['POST'])
@login_required
async def settings_avatar_post():
    # constants
    MAX_IMAGE_SIZE = glob.config.max_image_size * 1024 * 1024
    AVATARS_PATH = f'{glob.config.path_to_gulag}.data/avatars'
    ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png']

    avatar = (await request.files).get('avatar')

    # no file uploaded; deny post
    if avatar is None or not avatar.filename:
        return await flash('error', 'No image was selected!', 'settings/avatar')

    filename, file_extension = os.path.splitext(avatar.filename.lower())

    # bad file extension; deny post
    if not file_extension in ALLOWED_EXTENSIONS:
        return await flash('error', 'The image you select must be either a .JPG, .JPEG, or .PNG file!', 'settings/avatar')
    
    # check file size of avatar
    if avatar.content_length > MAX_IMAGE_SIZE:
        return await flash('error', 'The image you selected is too large!', 'settings/avatar')

    # remove old avatars
    for fx in ALLOWED_EXTENSIONS:
        if os.path.isfile(f'{AVATARS_PATH}/{session["user_data"]["id"]}{fx}'): # Checking file e
            os.remove(f'{AVATARS_PATH}/{session["user_data"]["id"]}{fx}')

    # avatar cropping to 1:1
    pilavatar = Image.open(avatar.stream)

    # avatar change success
    pilavatar = utils.crop_image(pilavatar)
    pilavatar.save(os.path.join(AVATARS_PATH, f'{session["user_data"]["id"]}{file_extension.lower()}'))
    return await flash('success', 'Your avatar has been successfully changed!', 'settings/avatar')

@frontend.route('/settings/custom')
@login_required
async def settings_custom():
    profile_customizations = utils.has_profile_customizations(session['user_data']['id'])
    return await render_template('settings/custom.html', customizations=profile_customizations)

@frontend.route('/settings/custom', methods=['POST'])
@login_required
async def settings_custom_post():
    files = await request.files
    banner = files.get('banner')
    background = files.get('background')
    ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png', '.gif']

    # no file uploaded; deny post
    if banner is None and background is None:
        return await flash_with_customizations('error', 'No image was selected!', 'settings/custom')

    if banner is not None and banner.filename:
        _, file_extension = os.path.splitext(banner.filename.lower())
        if not file_extension in ALLOWED_EXTENSIONS:
            return await flash_with_customizations('error', f'The banner you select must be either a .JPG, .JPEG, .PNG or .GIF file!', 'settings/custom')

        banner_file_no_ext = os.path.join(f'.data/banners', f'{session["user_data"]["id"]}')

        # remove old picture
        for ext in ALLOWED_EXTENSIONS:
            banner_file_with_ext = f'{banner_file_no_ext}{ext}'
            if os.path.isfile(banner_file_with_ext):
                os.remove(banner_file_with_ext)

        await banner.save(f'{banner_file_no_ext}{file_extension}')

    if background is not None and background.filename:
        _, file_extension = os.path.splitext(background.filename.lower())
        if not file_extension in ALLOWED_EXTENSIONS:
            return await flash_with_customizations('error', f'The background you select must be either a .JPG, .JPEG, .PNG or .GIF file!', 'settings/custom')

        background_file_no_ext = os.path.join(f'.data/backgrounds', f'{session["user_data"]["id"]}')

        # remove old picture
        for ext in ALLOWED_EXTENSIONS:
            background_file_with_ext = f'{background_file_no_ext}{ext}'
            if os.path.isfile(background_file_with_ext):
                os.remove(background_file_with_ext)

        await background.save(f'{background_file_no_ext}{file_extension}')

    return await flash_with_customizations('success', 'Your customisation has been successfully changed!', 'settings/custom')


@frontend.route('/settings/password')
@login_required
async def settings_password():
    return await render_template('settings/password.html')

@frontend.route('/settings/password', methods=["POST"])
@login_required
async def settings_password_post():
    form = await request.form
    old_password = form.get('old_password')
    new_password = form.get('new_password')
    repeat_password = form.get('repeat_password')

    # new password and repeat password don't match; deny post
    if new_password != repeat_password:
        return await flash('error', "Your new password doesn't match your repeated password!", 'settings/password')

    # new password and old password match; deny post
    if old_password == new_password:
        return await flash('error', 'Your new password cannot be the same as your old password!', 'settings/password')

    # Passwords must:
    # - be within 8-32 characters in length
    # - have more than 3 unique characters
    # - not be in the config's `disallowed_passwords` list
    if not 8 < len(new_password) <= 32:
        return await flash('error', 'Your new password must be 8-32 characters in length.', 'settings/password')

    if len(set(new_password)) <= 3:
        return await flash('error', 'Your new password must have more than 3 unique characters.', 'settings/password')

    if new_password.lower() in glob.config.disallowed_passwords:
        return await flash('error', 'Your new password was deemed too simple.', 'settings/password')

    # cache and other password related information
    bcrypt_cache = glob.cache['bcrypt']
    pw_bcrypt = (await glob.db.fetch(
        'SELECT pw_bcrypt '
        'FROM users '
        'WHERE id = %s',
        [session['user_data']['id']])
    )['pw_bcrypt'].encode()

    pw_md5 = hashlib.md5(old_password.encode()).hexdigest().encode()

    # check old password against db
    # intentionally slow, will cache to speed up
    if pw_bcrypt in bcrypt_cache:
        if pw_md5 != bcrypt_cache[pw_bcrypt]: # ~0.1ms
            if glob.config.debug:
                log(f"{session['user_data']['name']}'s change pw failed - pw incorrect.", Ansi.LYELLOW)
            return await flash('error', 'Your old password is incorrect.', 'settings/password')
    else: # ~200ms
        if not bcrypt.checkpw(pw_md5, pw_bcrypt):
            if glob.config.debug:
                log(f"{session['user_data']['name']}'s change pw failed - pw incorrect.", Ansi.LYELLOW)
            return await flash('error', 'Your old password is incorrect.', 'settings/password')

    # remove old password from cache
    if pw_bcrypt in bcrypt_cache:
        del bcrypt_cache[pw_bcrypt]

    # calculate new md5 & bcrypt pw
    pw_md5 = hashlib.md5(new_password.encode()).hexdigest().encode()
    pw_bcrypt = bcrypt.hashpw(pw_md5, bcrypt.gensalt())

    # update password in cache and db
    bcrypt_cache[pw_bcrypt] = pw_md5
    await glob.db.execute(
        'UPDATE users '
        'SET pw_bcrypt = %s '
        'WHERE safe_name = %s',
        [pw_bcrypt, utils.get_safe_name(session['user_data']['name'])]
    )

    # logout
    session.pop('authenticated', None)
    session.pop('user_data', None)
    return await flash('success', 'Your password has been changed! Please log in again.', 'login')


@frontend.route('/old/u/<id>')
async def old_profile_select(id):

    mode = request.args.get('mode', 'std', type=str) # 1. key 2. default value
    mods = request.args.get('mods', 'vn', type=str)
    user_data = await glob.db.fetch(
        'SELECT name, safe_name, id, priv, country '
        'FROM users '
        'WHERE safe_name = %s OR id = %s LIMIT 1',
        [utils.get_safe_name(id), id]
    )

    # no user
    if not user_data:
        return (await render_template('404.html'), 404)

    # make sure mode & mods are valid args
    if mode is not None and mode not in VALID_MODES:
        return (await render_template('404.html'), 404)

    if mods is not None and mods not in VALID_MODS:
        return (await render_template('404.html'), 404)

    is_staff = 'authenticated' in session and session['user_data']['is_staff']
    if not user_data or not (user_data['priv'] & Privileges.Normal or is_staff):
        return (await render_template('404.html'), 404)

    user_data['customisation'] = utils.has_profile_customizations(user_data['id'])
    return await render_template('old_profile.html', user=user_data, mode=mode, mods=mods)


@frontend.route('/leaderboard')
@frontend.route('/lb')
@frontend.route('/leaderboard/<mode>/<sort>/<mods>')
@frontend.route('/lb/<mode>/<sort>/<mods>')
async def leaderboard(mode='std', sort='pp', mods='vn'):
    return await render_template('leaderboard.html', mode=mode, sort=sort, mods=mods)

@frontend.route('/login')
async def login():
    if 'authenticated' in session:
        return await flash('error', "You're already logged in!", 'home')

    return await render_template('login.html')

@frontend.route('/login', methods=['POST'])
async def login_post():
    if 'authenticated' in session:
        return await flash('error', "You're already logged in!", 'home')

    if glob.config.debug:
        login_time = time.time_ns()

    form = await request.form
    username = form.get('username', type=str)
    passwd_txt = form.get('password', type=str)

    if username is None or passwd_txt is None:
        return await flash('error', 'Invalid parameters.', 'home')

    # check if account exists
    user_info = await glob.db.fetch(
        'SELECT id, name, email, priv, '
        'pw_bcrypt, silence_end, userpage_content, play_style, occupation_content, location_content, interest_content, username_aka '
        'FROM users '
        'WHERE safe_name = %s',
        [utils.get_safe_name(username)]
    )

    # fetch user stats
    user_info_stats = await glob.db.fetch(
        'SELECT id, mode, tscore, rscore, pp, plays, playtime, acc, max_combo, '
        'total_hits, replay_views, xh_count, x_count, sh_count, s_count, a_count '
        'FROM stats '
        'WHERE id = %s',
        [user_info['id']]
    )

    # user doesn't exist; deny post
    # NOTE: Bot isn't a user.
    if not user_info or user_info['id'] == 1:
        if glob.config.debug:
            log(f"{username}'s login failed - account doesn't exist.", Ansi.LYELLOW)
        return await flash('error', 'Account does not exist.', 'login')

    # cache and other related password information
    bcrypt_cache = glob.cache['bcrypt']
    pw_bcrypt = user_info['pw_bcrypt'].encode()
    pw_md5 = hashlib.md5(passwd_txt.encode()).hexdigest().encode()

    # check credentials (password) against db
    # intentionally slow, will cache to speed up
    if pw_bcrypt in bcrypt_cache:
        if pw_md5 != bcrypt_cache[pw_bcrypt]: # ~0.1ms
            if glob.config.debug:
                log(f"{username}'s login failed - pw incorrect.", Ansi.LYELLOW)
            return await flash('error', 'Password is incorrect.', 'login')
    else: # ~200ms
        if not bcrypt.checkpw(pw_md5, pw_bcrypt):
            if glob.config.debug:
                log(f"{username}'s login failed - pw incorrect.", Ansi.LYELLOW)
            return await flash('error', 'Password is incorrect.', 'login')

        # login successful; cache password for next login
        bcrypt_cache[pw_bcrypt] = pw_md5

    # user not verified; render verify
    if not user_info['priv'] & Privileges.Verified:
        if glob.config.debug:
            log(f"{username}'s login failed - not verified.", Ansi.LYELLOW)
        return await render_template('verify.html')

    # user banned; deny post
    if not user_info['priv'] & Privileges.Normal:
        if glob.config.debug:
            log(f"{username}'s login failed - banned.", Ansi.RED)
        return await flash('error', 'Your account is restricted. You are not allowed to log in.', 'login')

    # login successful; store session data
    if glob.config.debug:
        log(f"{username}'s login succeeded.", Ansi.LGREEN)

    session['authenticated'] = True
    session['user_data'] = {
        'id': user_info['id'],
        'name': user_info['name'],
        'email': user_info['email'],
        'priv': user_info['priv'],
        'about_me': user_info['userpage_content'],
        'playstyle': user_info['play_style'],
        'occupation': user_info['occupation_content'],
        'location': user_info['location_content'],
        'interest': user_info['interest_content'],
        'username_aka': user_info['username_aka'],
        'silence_end': user_info['silence_end'],
        'stats': {
            'pp': user_info_stats['pp']
        },
        'is_staff': user_info['priv'] & Privileges.Staff != 0,
        'is_nominator': user_info['priv'] & Privileges.Nominator != 0,
        'is_oguser': user_info['priv'] & Privileges.Oguser != 0,
        'is_donator': user_info['priv'] & Privileges.Donator != 0
    }

    if glob.config.debug:
        login_time = (time.time_ns() - login_time) / 1e6
        log(f'Login took {login_time:.2f}ms!', Ansi.LYELLOW)

    return redirect(url_for('frontend.home'))

@frontend.route('/register')
async def register():
    if 'authenticated' in session:
        return await flash('error', "You're already logged in.", 'home')

    if not glob.config.registration:
        return await flash('error', 'Registrations are currently disabled.', 'home')

    return await render_template('register.html')

@frontend.route('/register', methods=['POST'])
async def register_post():
    if 'authenticated' in session:
        return await flash('error', "You're already logged in.", 'home')

    if not glob.config.registration:
        return await flash('error', 'Registrations are currently disabled.', 'home')

    form = await request.form
    username = form.get('username', type=str)
    email = form.get('email', type=str)
    passwd_txt = form.get('password', type=str)
    key = form.get('key')

    if username is None or email is None or passwd_txt is None:
        return await flash('error', 'Invalid parameters.', 'home')

    # Usernames must:
    # - be within 2-15 characters in length
    # - not contain both ' ' and '_', one is fine
    # - not be in the config's `disallowed_names` list
    # - not already be taken by another player
    # check if username exists
    if not regexes.username.match(username):
        return await flash('error', 'Invalid username syntax.', 'register')

    if '_' in username and ' ' in username:
        return await flash('error', 'Username may contain "_" or " ", but not both.', 'register')

    if username in glob.config.disallowed_names:
        return await flash('error', 'Disallowed username; pick another.', 'register')

    if await glob.db.fetch('SELECT 1 FROM users WHERE name = %s', username):
        return await flash('error', 'Username already taken by another user.', 'register')

    # Emails must:
    # - match the regex `^[^@\s]{1,200}@[^@\s\.]{1,30}\.[^@\.\s]{1,24}$`
    # - not already be taken by another player
    if not regexes.email.match(email):
        return await flash('error', 'Invalid email syntax.', 'register')

    if await glob.db.fetch('SELECT 1 FROM users WHERE email = %s', email):
        return await flash('error', 'Email already taken by another user.', 'register')

    # handle invite key
    if key == "H4LOAL5VTHD9I6P20HCE":
        return await flash('error', 'Nice try...', 'register')

    if await glob.db.fetch('SELECT 1 FROM beta_keys WHERE beta_key = %s', key):
        key_valid = True
    else:
        return await flash('error', 'Invalid key.', 'register')

    if key_valid:
        used_key = await glob.db.fetch('SELECT used AS c FROM beta_keys WHERE beta_key = %s', key)
        if int(used_key['c']):
            return await flash('error', 'This key has already been used.', 'register')
    # key handle end

    # Passwords must:
    # - be within 8-32 characters in length
    # - have more than 3 unique characters
    # - not be in the config's `disallowed_passwords` list
    if not 8 <= len(passwd_txt) <= 32:
        return await flash('error', 'Password must be 8-32 characters in length.', 'register')

    if len(set(passwd_txt)) <= 3:
        return await flash('error', 'Password must have more than 3 unique characters.', 'register')

    if passwd_txt.lower() in glob.config.disallowed_passwords:
        return await flash('error', 'That password was deemed too simple.', 'register')

    # TODO: add correct locking
    # (start of lock)
    pw_md5 = hashlib.md5(passwd_txt.encode()).hexdigest().encode()
    pw_bcrypt = bcrypt.hashpw(pw_md5, bcrypt.gensalt())
    glob.cache['bcrypt'][pw_bcrypt] = pw_md5 # cache pw

    safe_name = utils.get_safe_name(username)

    # fetch the users' country
    if (
        request.headers and
        (ip := request.headers.get('X-Real-IP', type=str)) is not None
    ):
        country = await utils.fetch_geoloc(ip)
    else:
        country = 'xx'

    async with glob.db.pool.acquire() as conn:
        async with conn.cursor() as db_cursor:
            # add to `users` table.
            await db_cursor.execute(
                'INSERT INTO users '
                '(name, safe_name, email, pw_bcrypt, country, creation_time, latest_activity) '
                'VALUES (%s, %s, %s, %s, %s, UNIX_TIMESTAMP(), UNIX_TIMESTAMP())',
                [username, safe_name, email, pw_bcrypt, country]
            )
            user_id = db_cursor.lastrowid

            # add to `stats` table.
            await db_cursor.executemany(
                'INSERT INTO stats '
                '(id, mode) VALUES (%s, %s)',
                [(user_id, mode) for mode in (
                    0,  # vn!std
                    1,  # vn!taiko
                    2,  # vn!catch
                    3,  # vn!mania
                    4,  # rx!std
                    5,  # rx!taiko
                    6,  # rx!catch
                    8,  # ap!std
                )]
            )

    # (end of lock)

    if glob.config.debug:
        log(f'{username} has registered - awaiting verification.', Ansi.LGREEN)

    # user has successfully registered
    await glob.db.execute('UPDATE beta_keys SET used = 1 WHERE beta_key = %s', key)
    await glob.db.execute('UPDATE beta_keys SET user = %s WHERE beta_key = %s', [username, key])
    return await render_template('verify.html')

@frontend.route('/logout')
async def logout():
    if 'authenticated' not in session:
        return await flash('error', "You can't logout if you aren't logged in!", 'login')

    if glob.config.debug:
        log(f'{session["user_data"]["name"]} logged out.', Ansi.LGREEN)

    # clear session data
    session.pop('authenticated', None)
    session.pop('user_data', None)

    # render login
    return await flash('success', 'Successfully logged out!', 'login')

# social media redirections

@frontend.route('/github')
@frontend.route('/gh')
async def github_redirect():
    return redirect(glob.config.github)

@frontend.route('/discord')
async def discord_redirect():
    return redirect(glob.config.discord_server)

@frontend.route('/youtube')
@frontend.route('/yt')
async def youtube_redirect():
    return redirect(glob.config.youtube)

@frontend.route('/twitter')
async def twitter_redirect():
    return redirect(glob.config.twitter)

@frontend.route('/instagram')
@frontend.route('/ig')
async def instagram_redirect():
    return redirect(glob.config.instagram)

# profile customisation
BANNERS_PATH = Path.cwd() / '.data/banners'
DEFAULT_BANNER_PATH = Path.cwd() / 'static/images/default.jpg'
BACKGROUND_PATH = Path.cwd() / '.data/backgrounds'
@frontend.route('/banners/<user_id>')
async def get_profile_banner(user_id: int):
    # Check if avatar exists
    for ext in ('jpg', 'jpeg', 'png', 'gif'):
        path = BANNERS_PATH / f'{user_id}.{ext}'
        if path.exists():
            return await send_file(path)

    return await send_file(DEFAULT_BANNER_PATH)


@frontend.route('/backgrounds/<user_id>')
async def get_profile_background(user_id: int):
    # Check if avatar exists
    for ext in ('jpg', 'jpeg', 'png', 'gif'):
        path = BACKGROUND_PATH / f'{user_id}.{ext}'
        if path.exists():
            return await send_file(path)

    return b'{"status":404}'

@frontend.route('/score/<score_id>')
@frontend.route('/score/<score_id>/<mods>')
async def get_player_score(score_id:int=0, mods:str = "vn"):
    if score_id == 0:
        return await flash('error', "This score does not exist!", "home")
    if mods.lower() not in ["vn", "rx", "ap"]:
        return await flash('error', "Valid mods are vn, rx and ap!", "home")

    # Check score
    score = await glob.db.fetch("SELECT * FROM scores WHERE id=%s", score_id)
    if not score:
        return await flash('error', "Score not found!", "home")

    # Get user
    user = await glob.db.fetch("SELECT id, name, country, priv FROM users WHERE id=%s", score['userid'])

    if Privileges.Normal not in Privileges(int(user['priv'])):
        if not session:
            return (await render_template('404.html'), 404)
        elif Privileges.Admin not in Privileges(session['user_data']['priv']):
            return (await render_template('404.html'), 404)

    #Get Map
    map_info = await glob.db.fetch("SELECT artist, title, version AS diffname, creator, "
                                   "diff, mode, set_id, status, id, max_combo FROM maps WHERE md5=%s", score['map_md5'])
    if not map_info:
        log(f"Tried fetching scoreid {score_id} in {mods} (Route: /score/): Map with md5 '{score['map_md5']}' does not exist in database,"
        " that shouldn't happen unless you deleted it manually", Ansi.RED)
        return await flash('error', 'Could not display score, map does not exist in database', 'home')

    #Change variables and stuff like that
    try:
        map_info['diff'] = round(map_info['diff'], 2)
    except:
        map_info['diff'] = map_info['diff']
    score['grade'] = score['grade'].upper()
    user['country'] = user['country'].upper()
    score['play_time'] = str(score['play_time'])
    year = int(score['play_time'].split(" ")[0].split("-")[0])
    month = int(score['play_time'].split(" ")[0].split("-")[1])
    day = int(score['play_time'].split(" ")[0].split("-")[2])
    hour = int(score['play_time'].split(" ")[1].split(":")[0])
    minute = int(score['play_time'].split(" ")[1].split(":")[1])
    second = int(score['play_time'].split(" ")[1].split(":")[2])
    score['play_time'] = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)} {str(hour).zfill(2)}:{str(minute).zfill(2)}:{str(second).zfill(2)}"
    user['banner'] = f"url(https://meow.nya/banners/{user['id']});"
    user['background'] = f"https://meow.nya/backgrounds/{user['id']}"
    map_info['banner_link'] = f"url('https://assets.ppy.sh/beatmaps/{map_info['set_id']}/covers/cover.jpg');"
    score['acc'] = f"{round(float(score['acc']), 2)}%"
    score['pp'] = round(float(score['pp']), 2)
    score['max_combo_fix'] = f"{score['max_combo']}x"
    #Calculation
    grade_colors= {
        "F": "#ff5959",
        "D": "#ff5959",
        "C": "#ff56da",
        "B": "#3d97ff",
        "A": "#2bff35",
        "S": "#ffcc22",
        "SH": "#cde7e7",
        "X": "#ffcc22",
        "XH": "#cde7e7",
    }
    try:
        grade_shadow = grade_colors[score['grade'].upper()]
    except:
        grade_shadow = "#FFFFFF"

    grade_convert = {"XH": "SS", "X": "SS", "SH": "S"}
    try:
        score['grade'] = grade_convert[score['grade']]
    except:
        score['grade'] = score['grade']
    #add commas to score
    score['score'] = "{:,}".format(int(score['score']))
    #Make badges
    user_priv = Privileges(user['priv'])
    group_list = []
    if Privileges.Normal not in user_priv:
        group_list.append(["RESTRICTED", "#FFFFFF"])
    else:
        if int(user['id']) in [3]:
            group_list.append(["OWNER", "#e84118"])
        if Privileges.Dangerous in user_priv:
            group_list.append(["DEV", "#9b59b6"])
        elif Privileges.Admin in user_priv:
            group_list.append(["ADM", "#fbc531"])
        elif Privileges.Mod in user_priv:
            group_list.append(["GMT", "#28a40c"])
        if Privileges.Nominator in user_priv:
            group_list.append(["BN", "#1e90ff"])
        #if Privileges.Alumni in user_priv:
            #group_list.append(["ALU", "#ea8685"])
        if Privileges.Supporter in user_priv:
            if Privileges.Premium in user_priv:
                group_list.append(["❤❤", "#f78fb3"])
            else:
                group_list.append(["❤", "#f78fb3"])
        elif Privileges.Premium in user_priv:
            group_list.append(["❤❤", "#f78fb3"])
        if Privileges.Whitelisted in user_priv:
            group_list.append(["✔️", "#28a40c"])

    #Get status
    async with glob.http.get(f"https://api.komako.pw/get_player_status?id={user['id']}") as resp:
        resp = await resp.json()
        if resp['player_status']['online'] == True:
            player_status = ["#38c714", "Online"]
        else:
            player_status = ["#000000", "Offline"]

    #Mods
        if score['mods'] != 0:
            score['mods'] = f"{Mods(int(score['mods']))!r}"

    return await render_template('score.html', user_banner=user['background'], score=score, user=user, map_info=map_info, grade_shadow=grade_shadow, group_list=group_list, player_status=player_status, mode_mods=mods)

@frontend.route('/b/<bid>')
@frontend.route('/beatmaps/<bid>')
async def beatmappage_id(bid):

    beatmap_data = await glob.db.fetch("SELECT * FROM maps WHERE id = %s",
        [bid]
    )
    
    if not beatmap_data:
        return (await render_template('404.html'), 404)

    set_data = await glob.db.fetchall("SELECT * FROM maps WHERE set_id = %s ORDER BY diff ASC",
        [beatmap_data["set_id"]]
    )

    all_diffs = await glob.db.fetchall(
        'SELECT id, set_id, version diff '
        'FROM maps '
        'WHERE set_id = %s '
        'ORDER BY diff ASC',
        [beatmap_data["set_id"]]
    )

    print(set_data)
    print(all_diffs)

    return await render_template('beatmap.html',bid=bid,beatmap_data=beatmap_data, set_data=set_data, timeago=timeago, all_diffs=all_diffs)

@frontend.route('/maps')
async def maps():

    custom_ranked = await glob.db.fetchall(
        'SELECT id, set_id, status, artist, title, creator, frozen, plays '
        'FROM maps '
        'WHERE frozen = 1 and status = 2 '
        'GROUP BY id, set_id, status, artist, title, creator, frozen, plays '
        'ORDER BY RAND() '
        'LIMIT 48'
    )

    return await render_template('maps.html', custom_ranked=custom_ranked)

@frontend.route('/documentation')
async def documentation():
    return await render_template('documentation/documentation.html')

@frontend.route('/documentation/appeal')
async def documentation_appeal():
    return await render_template('documentation/appeal.html')

@frontend.route('/documentation/rules')
async def documentation_rules():
    return await render_template('documentation/rules.html')

@frontend.route('/documentation/privacy')
async def documentation_privacy():
    return await render_template('documentation/privacy.html')

@frontend.route('/documentation/faq')
async def documentation_faq():
    return await render_template('documentation/faq.html')

@frontend.route('/documentation/connect')
async def documentation_connect():
    return await render_template('documentation/connect.html')

@frontend.route('/team')
async def team():
    return await render_template('team.html')

@frontend.route('/support')
async def support():
    return await render_template('support.html')

@frontend.route('/support/purchase')
async def support_purchase():

    if not 'authenticated' in session:
        return await flash('error', 'Please login first.', 'login')

    if not session["user_data"]["is_staff"]:
        return await flash('error', 'You are now allowed back here...', 'login')

    return await render_template('purchase.html')

@frontend.route('/friends')
@login_required
async def friends_page():
    user_id = session['user_data']['id']

    friends = await glob.db.fetchall(
        'SELECT user2 FROM relationships '
        'WHERE user1 = %s AND type = "friend"',
        [user_id]
    )

    async def get_friend_info(friend_id):
        if friend_id == 1:  # bot
            bot_info = await glob.db.fetch(
                'SELECT name, country FROM users '
                'WHERE id = 1'
            )
            return {
                'id': bot_info['id'],
                'name': bot_info['name'],
                'country': bot_info['country'],
                'priv': bot_info['priv'],
                'status': True,
                'customisation': utils.has_profile_customizations(friend_id),
                'mutual': False
            }

        friend_status = requests.get(f'http://bancho/v1/get_player_status?id={friend_id}', headers={'Host':'api.meow.nya'})
        friend_status = json.loads(friend_status.content)
        status = friend_status['player_status']['online']
        if 'player_status' in friend_status and 'last_seen' in friend_status['player_status']:
            last_seen = "just now!" if status is None else timeago.format(friend_status['player_status']['last_seen'], time.time())
        else:
            last_seen = "just now!"  # or assign a default value if needed

        friend_data = requests.get(f'http://bancho/v1/get_player_info?id={friend_id}&scope=info', headers={'Host':'api.meow.nya'})
        friend_data = json.loads(friend_data.content)
        name = friend_data['player']['info']['name']
        country = friend_data['player']['info']['country']
        priv = friend_data['player']['info']['priv']
        id = friend_data['player']['info']['id']

        mutual_relationship = await glob.db.fetchall(
            'SELECT user2 FROM relationships '
            'WHERE user1 = %s AND user2 = %s AND type = "friend"',
            [friend_id, user_id]
        )
        
        return {
            'id': id,
            'name': name,
            'country': country,
            'priv': priv,
            'status': status,
            'last_seen': last_seen,
            'customisation': utils.has_profile_customizations(friend_id),
            'mutual': mutual_relationship
        }

    friends_info = await asyncio.gather(*[get_friend_info(friend['user2']) for friend in friends])
    friends = [dict(friend, **info) for friend, info in zip(friends, friends_info)]

    return await render_template('friends.html', friends=friends, timeago=timeago)

@frontend.route('/u/<id>')
async def profile_select(id):

    mode = request.args.get('mode', 'std', type=str) # 1. key 2. default value
    mods = request.args.get('mods', 'vn', type=str)
    user_data = await glob.db.fetch(
        'SELECT name, safe_name, id, priv, country, userpage_content, username_aka, latest_activity, creation_time, play_style, occupation_content, location_content, interest_content '
        'FROM users '
        'WHERE safe_name = %s OR id = %s LIMIT 1',
        [utils.get_safe_name(id), id]
    )

    #about_me/userpage_content
    rendered_bbcode = bbcode(escape(user_data['userpage_content']))

    # no user
    if not user_data:
        return (await render_template('404.html'), 404)

    # make sure mode & mods are valid args
    if mode is not None and mode not in VALID_MODES:
        return (await render_template('404.html'), 404)

    if mods is not None and mods not in VALID_MODS:
        return (await render_template('404.html'), 404)

    is_staff = 'authenticated' in session and session['user_data']['is_staff']
    if not user_data or not (user_data['priv'] & Privileges.Normal or is_staff):
        return (await render_template('404.html'), 404)

    user_data['customisation'] = utils.has_profile_customizations(user_data['id'])

    follow_count = await glob.db.fetch(
        'SELECT COUNT(*) AS follow_count '
        'FROM relationships '
        'WHERE user2 = (%s)',
        [id]
    )

    meta_stats = await glob.db.fetch(
        'SELECT id, mode, tscore, rscore, pp, plays, playtime, acc, max_combo, total_hits, replay_views, xh_count, x_count, sh_count, s_count, a_count '
        'FROM stats '
        'WHERE id IN (%s, %s) AND mode = 0 LIMIT 1',
        (id, utils.get_safe_name(id))
    )

    favourites_data = await glob.db.fetchall(
        'SELECT f.userid, f.setid, f.created_at, m.status, m.creator, m.artist, m.title '
        'FROM favourites f '
        'JOIN maps m ON f.setid = m.set_id '
        'WHERE f.userid IN (%s) '
        'GROUP BY f.userid, f.setid, f.created_at, m.status, m.creator, m.artist, m.title ',
        [id]
    )

    favourites_count = await glob.db.fetch(
        'SELECT COUNT(DISTINCT setid) AS fav_count '
        'FROM favourites '
        'WHERE userid in (%s) ',
        [id]
    )

    #Make badges
    user_priv = Privileges(user_data['priv'])
    group_list = []
    if Privileges.Normal not in user_priv:
        group_list.append(["RESTRICTED", "#ff0000", "fa-ban"])
    else:
        if int(user_data['id']) in [3]:
            group_list.append(["Owner", "#e27030", "fa-cat"])
        if Privileges.Dangerous in user_priv:
            group_list.append(["Developer", "#515981", "fa-code"])
        #elif Privileges.Admin in user_priv:
            #group_list.append(["ADM", "#fbc531", ""])
        #elif Privileges.Mod in user_priv:
            #group_list.append(["GMT", "#28a40c", ""])
        if Privileges.Nominator in user_priv:
            group_list.append(["BAT", "#30E2BF", "fa-music"])
        if Privileges.Alumni in user_priv:
            group_list.append(["Alumni", "#ea8685", "fa-door-open"])
        if int(user_data["id"]) in [3]:
            group_list.append(["Neko", "#FA6F5D", "fa-paw"])
        if Privileges.Oguser in user_priv:
            group_list.append(["OG", "#e88d15", "fa-frog"])
        if Privileges.Supporter in user_priv:
            if Privileges.Premium in user_priv:
                group_list.append(["Premium", "#f78fb3", "fa-fire"])
            else:
                group_list.append(["Supporter", "#f78fb3", "fa-heart"])

            

    badges = []

    if user_data["priv"] & Privileges.Dangerous:
        badges.append(("Developer", "fa-code", 7))
    #if user_data["priv"] & Privileges.Admin:
        #badges.append(("Administrator", "fa-user", 9.6))
    #if user_data["priv"] & Privileges.Mod:
        #badges.append(("Moderator", "fa-user-check", 8))
    if user_data["priv"] & Privileges.Nominator:
        badges.append(("Nominator", "fa-music", 8))
    if user_data["priv"] & Privileges.Supporter:
        badges.append(("Donator", "fa-dollar-sign", 11.4))
    if user_data["priv"] & Privileges.Whitelisted:
        badges.append(("Verified", "fa-check", 9.6))

    ## Custom badges
    if user_data["id"] == 0:
        badges.append(("Developer", "fa-code", 7))
    if user_data["id"] == 0:
        badges.append(("Skylar <3", "fa-music", 6,6))
    elif user_data["id"] == 0:
        badges.append(("Racist", "fa-church", 7))
    if user_data["id"] == 4:
        badges.append(("Verified", "fa-check", 9.6))
    if user_data["id"] == 5:
        badges.append(("Verified", "fa-check", 9.6))
    if user_data["id"] == 10:
        badges.append(("Verified", "fa-check", 9.6))
    if user_data["id"] == 6:
        badges.append(("Verified", "fa-check", 9.6))
    if user_data["id"] == 33:
        badges.append(("Verified", "fa-check", 9.6))
    if user_data["id"] == 47:
        badges.append(("Verified", "fa-check", 9.6))
    if user_data["id"] == 3:
        badges.append(("Cutie", "fa-heart", 8.6))
    if user_data["id"] == 7:
        badges.append(("Cutie", "fa-heart", 9.6))
    if user_data["id"] == 6:
        badges.append(("Cutie", "fa-heart", 9.6))
    if user_data["id"] == 26:
        badges.append(("Cutie", "fa-heart", 9.6))
    if user_data["id"] == 28:
        badges.append(("Cutie", "fa-heart", 9.6))
    if user_data["id"] == 32:
        badges.append(("Cutie", "fa-heart", 8))
    if user_data["id"] == 33:
        badges.append(("Beweger", "fa-jet-fighter", 7))
    if user_data["id"] == 34:
        badges.append(("Beweger", "fa-jet-fighter", 7))
    if user_data["id"] == 3: 
        badges.append(("Hacker", "fa-ban", 8.6))
    if user_data["id"] == 25:
        badges.append(("Hacker", "fa-ban", 8.6))
    user_data['creation_time'] = datetime.fromtimestamp(float(user_data['creation_time']))
    user_data['latest_activity'] = datetime.fromtimestamp(float(user_data['latest_activity']))
    user_data['customisation'] = utils.has_profile_customizations(user_data['id'])

    # Get play_style value from column
    playstyle_data = await glob.db.fetch(
        'SELECT id, play_style FROM users '
        'WHERE id = %s',
        [id]
    )

    # Extract the play_style value from the dictionary
    playstyle_value = playstyle_data['play_style']

    # Calculate playstyle_names_str based on playstyle_value
    playstyle_names = []

    # Calculate playstyle_names_str based on playstyle_value
    playstyle_names = []

    if playstyle_value & 1:
        playstyle_names.append('tablet')
    if playstyle_value & 2:
        playstyle_names.append('mouse')
    if playstyle_value & 4:
        playstyle_names.append('keyboard')
    if playstyle_value & 8:
        playstyle_names.append('touch')

    playstyle_names_str = ', '.join(playstyle_names)

    # Calculate the player's level and level progress
    # total_score = meta_stats['tscore']  # Assuming 'tscore' holds the total score
    # player_level = get_level(total_score)
    # current_level_score = get_required_score_for_level(player_level)
    # next_level_score = get_required_score_for_level(player_level + 1)
    # level_progress = ((total_score - current_level_score) / (next_level_score - current_level_score)) * 100 | , player_level=player_level, level_progress=level_progress

    recent_activity = await glob.db.fetchall(
        'SELECT sl.*, u.name, m.id AS map_id, m.title AS map_title, m.version, '
        'sniped_user.name AS sniped_name, sniped_user.id AS sniper_id, m.mode '
        'FROM ( '
        '    SELECT * '
        '    FROM ( '
        '        SELECT *, '
        '               ROW_NUMBER() OVER(PARTITION BY map_md5 ORDER BY timestamp DESC) AS rn '
        '        FROM score_logs '
        '        WHERE user_id = %s '
        '    ) AS ranked_logs '
        '    WHERE rn = 1 '
        ') AS sl '
        'JOIN users u ON sl.user_id = u.id '
        'JOIN maps m ON sl.map_md5 = m.md5 '
        'LEFT JOIN users sniped_user ON sl.got_sniped_by = sniped_user.name '
        'ORDER BY sl.timestamp DESC LIMIT 5', [id]
    )

    mode_strings = {
        '0': "(osu!std)",
        '4': "(osu!rx)",
        '8': "(osu!ap)"
    }

    user_rank_1_maps = set()

    return await render_template('profile.html', user=user_data, mode=mode, mods=mods, rendered_bbcode=rendered_bbcode, follow_count=follow_count,
                                 timeago=timeago, playstyle_names_str=playstyle_names_str, datetime=datetime, group_list=group_list,
                                 badges=badges, meta_stats=meta_stats, recent_activity=recent_activity, mode_strings=mode_strings, 
                                 user_rank_1_maps=user_rank_1_maps, favourites_data=favourites_data, favourites_count=favourites_count)