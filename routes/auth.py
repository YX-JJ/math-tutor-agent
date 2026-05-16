from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import hashlib
from config import get_config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        cfg = get_config()

        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

        if username == cfg.get('teacher_username') and password_hash == cfg.get('teacher_password_hash'):
            session['teacher_logged_in'] = True
            session['teacher_username'] = username
            return redirect(url_for('teacher.dashboard'))
        else:
            flash('用户名或密码错误', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
