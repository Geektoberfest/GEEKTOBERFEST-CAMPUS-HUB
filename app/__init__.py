import os
from pathlib import Path
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv
from app.extensions import db, login_manager, csrf
from config import Config

load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request_wants_json():
            return jsonify(error='Authentication required'), 401
        from flask import redirect, url_for, flash
        if login_manager.login_message:
            flash(login_manager.login_message)
        return redirect(url_for(login_manager.login_view))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        from datetime import date
        from app.services.i18n import translate, get_current_language, SUPPORTED_LANGUAGES
        return {
            'app_name': 'CampusHub',
            'now_date': date.today(),
            't': translate,
            'current_lang': get_current_language(),
            'supported_languages': SUPPORTED_LANGUAGES
        }


    @app.template_filter('relative_time')
    def relative_time(dt):
        if not dt: return ''
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return 'just now'
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        if days < 30:
            return f"{days} day{'s' if days != 1 else ''} ago"
        months = days // 30
        if months < 12:
            return f"{months} month{'s' if months != 1 else ''} ago"
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"

    @app.errorhandler(400)
    def bad_request(e):
        if request_wants_json(): return jsonify(error='Bad request'), 400
        return render_template('error.html', code=400, message='The request could not be processed.'), 400
    @app.errorhandler(401)
    def unauthorized(e):
        if request_wants_json(): return jsonify(error='Authentication required'), 401
        return render_template('error.html', code=401, message='Please log in to continue.'), 401
    @app.errorhandler(403)
    def forbidden(e):
        if request_wants_json(): return jsonify(error='Forbidden'), 403
        return render_template('error.html', code=403, message='You do not have permission to do that.'), 403
    @app.errorhandler(404)
    def not_found(e):
        if request_wants_json(): return jsonify(error='Not found'), 404
        return render_template('error.html', code=404, message='The page or resource was not found.'), 404
    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        if request_wants_json(): return jsonify(error='Internal server error'), 500
        return render_template('error.html', code=500, message='Something went wrong. Please try again.'), 500

    with app.app_context():
        db.create_all()
        if app.config.get('SEED_ON_START', False):
            from app.seed import seed_database
            seed_database()
    return app

def request_wants_json():
    from flask import request
    return request.path.startswith('/api/') or request.accept_mimetypes.best == 'application/json'
