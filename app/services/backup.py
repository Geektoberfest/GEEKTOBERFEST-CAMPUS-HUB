import json
import os
import shutil
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from flask import current_app
from app.extensions import db
from app.models import User, Task, Note, Resource, Announcement, Notification


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)



def _serialize_datetime(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return str(val)


def _parse_datetime(val):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _parse_date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _get_sqlite_path():
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if uri.startswith('sqlite:///'):
        db_path = uri.replace('sqlite:///', '')
        return Path(db_path)
    return None


def create_backup(output_path=None, format='json'):
    format = format.lower()
    if format not in ('json', 'sqlite'):
        raise ValueError("Unsupported format. Choose 'json' or 'sqlite'.")

    backups_dir = Path(current_app.instance_path) / 'backups'
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = utcnow().strftime('%Y%m%d_%H%M%S')

    if format == 'sqlite':
        sqlite_file = _get_sqlite_path()
        if not sqlite_file or not sqlite_file.exists():
            raise RuntimeError("SQLite backup format is only supported when using an SQLite database.")
        
        target_path = Path(output_path) if output_path else (backups_dir / f"campushub_backup_{timestamp}.db")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Use sqlite3 online backup API for safe consistent copy
        src_conn = sqlite3.connect(str(sqlite_file))
        dst_conn = sqlite3.connect(str(target_path))
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

        return {
            'path': str(target_path),
            'format': 'sqlite',
            'timestamp': timestamp,
            'size_bytes': target_path.stat().st_size
        }

    # JSON format backup
    target_path = Path(output_path) if output_path else (backups_dir / f"campushub_backup_{timestamp}.json")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    users = [{
        'id': u.id,
        'name': u.name,
        'email': u.email,
        'password_hash': u.password_hash,
        'role': u.role,
        'department': u.department,
        'year': u.year,
        'avatar': u.avatar,
        'joined_at': _serialize_datetime(u.joined_at)
    } for u in User.query.order_by(User.id.asc()).all()]

    tasks = [{
        'id': t.id,
        'user_id': t.user_id,
        'title': t.title,
        'description': t.description,
        'priority': t.priority,
        'category': t.category,
        'due_date': _serialize_datetime(t.due_date),
        'completed': t.completed,
        'created_at': _serialize_datetime(t.created_at),
        'updated_at': _serialize_datetime(t.updated_at)
    } for t in Task.query.order_by(Task.id.asc()).all()]

    notes = [{
        'id': n.id,
        'user_id': n.user_id,
        'title': n.title,
        'content': n.content,
        'subject': n.subject,
        'created_at': _serialize_datetime(n.created_at),
        'updated_at': _serialize_datetime(n.updated_at)
    } for n in Note.query.order_by(Note.id.asc()).all()]

    resources = [{
        'id': r.id,
        'title': r.title,
        'description': r.description,
        'subject': r.subject,
        'resource_type': r.resource_type,
        'url': r.url,
        'added_by': r.added_by,
        'created_at': _serialize_datetime(r.created_at)
    } for r in Resource.query.order_by(Resource.id.asc()).all()]

    announcements = [{
        'id': a.id,
        'title': a.title,
        'content': a.content,
        'category': a.category,
        'priority': a.priority,
        'created_at': _serialize_datetime(a.created_at),
        'updated_at': _serialize_datetime(a.updated_at)
    } for a in Announcement.query.order_by(Announcement.id.asc()).all()]

    notifications = [{
        'id': n.id,
        'user_id': n.user_id,
        'title': n.title,
        'message': n.message,
        'kind': n.kind,
        'read': n.read,
        'created_at': _serialize_datetime(n.created_at)
    } for n in Notification.query.order_by(Notification.id.asc()).all()]

    counts = {
        'users': len(users),
        'tasks': len(tasks),
        'notes': len(notes),
        'resources': len(resources),
        'announcements': len(announcements),
        'notifications': len(notifications)
    }

    payload = {
        'version': '1.0',
        'type': 'campushub_database_backup',
        'timestamp': utcnow().isoformat() + 'Z',
        'counts': counts,
        'data': {
            'users': users,
            'tasks': tasks,
            'notes': notes,
            'resources': resources,
            'announcements': announcements,
            'notifications': notifications
        }
    }

    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return {
        'path': str(target_path),
        'format': 'json',
        'timestamp': timestamp,
        'counts': counts,
        'size_bytes': target_path.stat().st_size
    }


def restore_backup(input_path, create_safety_backup=True):
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Backup file not found: {input_path}")

    # Inspect file format
    with open(path, 'rb') as f:
        header = f.read(16)

    is_sqlite = header.startswith(b'SQLite format 3')

    safety_backup_path = None
    if create_safety_backup:
        try:
            safety_res = create_backup(format='json')
            safety_backup_path = safety_res['path']
        except Exception:
            # Continue even if safety backup fails (e.g. empty or fresh db)
            pass

    if is_sqlite:
        sqlite_file = _get_sqlite_path()
        if not sqlite_file:
            raise RuntimeError("Cannot restore SQLite backup into a non-SQLite database configuration.")
        
        db.session.remove()
        db.engine.dispose()

        src_conn = sqlite3.connect(str(path))
        dst_conn = sqlite3.connect(str(sqlite_file))
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

        return {
            'format': 'sqlite',
            'safety_backup_path': safety_backup_path,
            'path': str(path)
        }

    # JSON Restore
    with open(path, 'r', encoding='utf-8') as f:
        try:
            payload = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted or invalid JSON backup file: {e}")

    if not isinstance(payload, dict) or 'data' not in payload:
        raise ValueError("Invalid backup structure: missing 'data' root element.")

    data = payload['data']
    for req_table in ('users', 'tasks', 'notes', 'resources', 'announcements', 'notifications'):
        if req_table not in data or not isinstance(data[req_table], list):
            raise ValueError(f"Invalid backup structure: missing or invalid '{req_table}' table.")

    try:
        # Clear existing records in proper foreign key order
        Notification.query.delete()
        Task.query.delete()
        Note.query.delete()
        Resource.query.delete()
        Announcement.query.delete()
        User.query.delete()
        db.session.flush()

        # Restore Users
        for u_data in data['users']:
            u = User(
                id=u_data['id'],
                name=u_data['name'],
                email=u_data['email'],
                password_hash=u_data['password_hash'],
                role=u_data.get('role', 'student'),
                department=u_data.get('department', ''),
                year=u_data.get('year', ''),
                avatar=u_data.get('avatar', ''),
                joined_at=_parse_datetime(u_data.get('joined_at')) or utcnow()
            )
            db.session.add(u)
        db.session.flush()

        # Restore Announcements
        for a_data in data['announcements']:
            a = Announcement(
                id=a_data['id'],
                title=a_data['title'],
                content=a_data['content'],
                category=a_data.get('category', 'General'),
                priority=a_data.get('priority', 'Normal'),
                created_at=_parse_datetime(a_data.get('created_at')) or utcnow(),
                updated_at=_parse_datetime(a_data.get('updated_at')) or utcnow()
            )
            db.session.add(a)

        # Restore Resources
        for r_data in data['resources']:
            r = Resource(
                id=r_data['id'],
                title=r_data['title'],
                description=r_data.get('description', ''),
                subject=r_data.get('subject', 'General'),
                resource_type=r_data.get('resource_type', 'Other'),
                url=r_data['url'],
                added_by=r_data.get('added_by'),
                created_at=_parse_datetime(r_data.get('created_at')) or utcnow()
            )
            db.session.add(r)

        # Restore Notes
        for n_data in data['notes']:
            n = Note(
                id=n_data['id'],
                user_id=n_data['user_id'],
                title=n_data['title'],
                content=n_data['content'],
                subject=n_data.get('subject', 'General'),
                created_at=_parse_datetime(n_data.get('created_at')) or utcnow(),
                updated_at=_parse_datetime(n_data.get('updated_at')) or utcnow()
            )
            db.session.add(n)

        # Restore Tasks
        for t_data in data['tasks']:
            t = Task(
                id=t_data['id'],
                user_id=t_data['user_id'],
                title=t_data['title'],
                description=t_data.get('description', ''),
                priority=t_data.get('priority', 'medium'),
                category=t_data.get('category', 'other'),
                due_date=_parse_date(t_data.get('due_date')),
                completed=bool(t_data.get('completed', False)),
                created_at=_parse_datetime(t_data.get('created_at')) or utcnow(),
                updated_at=_parse_datetime(t_data.get('updated_at')) or utcnow()
            )
            db.session.add(t)

        # Restore Notifications
        for notif_data in data['notifications']:
            notif = Notification(
                id=notif_data['id'],
                user_id=notif_data['user_id'],
                title=notif_data['title'],
                message=notif_data['message'],
                kind=notif_data.get('kind', 'info'),
                read=bool(notif_data.get('read', False)),
                created_at=_parse_datetime(notif_data.get('created_at')) or utcnow()
            )
            db.session.add(notif)

        db.session.commit()

        restored_counts = {k: len(v) for k, v in data.items()}
        return {
            'format': 'json',
            'safety_backup_path': safety_backup_path,
            'restored_counts': restored_counts,
            'path': str(path)
        }
    except Exception:
        db.session.rollback()
        raise
