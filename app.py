from flask import Flask
from config import get_secret_key
from routes.auth import auth_bp
from routes.teacher import teacher_bp
from routes.student import student_bp
from routes.api import api_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = get_secret_key()

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        from flask import redirect, url_for, session
        if session.get('teacher_logged_in'):
            return redirect(url_for('teacher.dashboard'))
        return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('error.html', code=404, message='页面未找到'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('error.html', code=500, message='服务器内部错误'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print('=' * 50)
    print('  初中数学教学智能体')
    print('  本机访问: http://localhost:5000')
    print(f'  局域网访问: http://{local_ip}:5000')
    print('  默认账号: admin / admin123')
    print('=' * 50)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
