import json
from pathlib import Path
from datetime import date
from app.extensions import db
from app.models import User, Task, Note, Resource, Announcement, Notification
from app.services.backup import create_backup, restore_backup


def test_create_backup_json(app, student):
    with app.app_context():
        user = db.session.get(User, student)
        t = Task(user_id=user.id, title='Study Algorithms', priority='high', due_date=date.today())
        n = Note(user_id=user.id, title='Algo Notes', content='Graph algorithms...')
        db.session.add_all([t, n])
        db.session.commit()

        res = create_backup(format='json')
        assert res['format'] == 'json'
        backup_path = Path(res['path'])
        assert backup_path.exists()
        assert res['counts']['users'] >= 1
        assert res['counts']['tasks'] >= 1
        assert res['counts']['notes'] >= 1

        with open(backup_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['type'] == 'campushub_database_backup'
        assert len(data['data']['tasks']) >= 1
        assert data['data']['tasks'][0]['title'] == 'Study Algorithms'


def test_create_backup_sqlite(app, student):
    with app.app_context():
        res = create_backup(format='sqlite')
        assert res['format'] == 'sqlite'
        backup_path = Path(res['path'])
        assert backup_path.exists()
        assert backup_path.stat().st_size > 0


def test_restore_backup_json(app, student, tmp_path):
    backup_file = tmp_path / 'test_backup.json'

    with app.app_context():
        user = db.session.get(User, student)
        t1 = Task(user_id=user.id, title='Task 1', completed=False)
        t2 = Task(user_id=user.id, title='Task 2', completed=True)
        note = Note(user_id=user.id, title='My Note', content='Some content')
        ann = Announcement(title='Exam Schedule', content='Finals next week.')
        db.session.add_all([t1, t2, note, ann])
        db.session.commit()

        # Create backup to tmp_path
        create_backup(output_path=backup_file, format='json')

        # Now mutate/delete data
        Task.query.delete()
        Note.query.delete()
        Announcement.query.delete()
        db.session.commit()

        assert Task.query.count() == 0
        assert Note.query.count() == 0
        assert Announcement.query.count() == 0

        # Restore from backup
        res = restore_backup(backup_file, create_safety_backup=True)
        assert res['format'] == 'json'
        assert Task.query.count() == 2
        assert Note.query.count() == 1
        assert Announcement.query.count() == 1
        assert Task.query.filter_by(title='Task 1').first() is not None
        assert Task.query.filter_by(title='Task 2').first().completed is True


def test_restore_invalid_file_handling(app, tmp_path):
    with app.app_context():
        # Non-existent file
        try:
            restore_backup(tmp_path / 'non_existent.json')
            assert False, "Should raise FileNotFoundError"
        except FileNotFoundError:
            pass

        # Corrupted JSON
        bad_json = tmp_path / 'bad.json'
        bad_json.write_text('{"incomplete": true, ')
        try:
            restore_backup(bad_json)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

        # Missing 'data' root
        malformed = tmp_path / 'malformed.json'
        malformed.write_text(json.dumps({'foo': 'bar'}))
        try:
            restore_backup(malformed)
            assert False, "Should raise ValueError"
        except ValueError:
            pass


def test_cli_db_backup(app, student):
    runner = app.test_cli_runner()
    result = runner.invoke(args=['db-backup'])
    assert result.exit_code == 0
    assert 'Backup created successfully' in result.output


def test_cli_db_restore_safeguard(app, tmp_path, student):
    runner = app.test_cli_runner()
    backup_file = tmp_path / 'cli_backup.json'

    with app.app_context():
        create_backup(output_path=backup_file, format='json')

    # Run without --yes and input 'n' -> should abort
    result = runner.invoke(args=['db-restore', '-i', str(backup_file)], input='n\n')
    assert result.exit_code != 0

    # Run with --yes -> should succeed
    result = runner.invoke(args=['db-restore', '-i', str(backup_file), '--yes'])
    assert result.exit_code == 0
    assert 'Database restored successfully' in result.output
