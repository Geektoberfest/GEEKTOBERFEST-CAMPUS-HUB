from datetime import date
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.extensions import db
from app.models import Task, Note, Resource, Announcement, Notification, StudySession
from app.services.dashboard import dashboard_stats, generate_notifications
from app.services.study_planner import generate_study_schedule, save_study_schedule
from app.utils.validation import clean, limited, valid_url


main_bp=Blueprint('main',__name__)

@main_bp.get('/')
def index(): return redirect(url_for('main.dashboard')) if current_user.is_authenticated else redirect(url_for('auth.login'))

@main_bp.get('/dashboard')
@login_required
def dashboard():
    period=request.args.get('period','7d')
    start_date=request.args.get('start_date')
    end_date=request.args.get('end_date')
    generate_notifications(current_user)
    return render_template('dashboard.html', stats=dashboard_stats(current_user,start_date=start_date,end_date=end_date,period=period))

@main_bp.get('/tasks')
@login_required
def tasks(): return render_template('tasks.html', tasks=Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all())

@main_bp.get('/tasks/export')
@login_required
def export_tasks_route():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all()
    tasks_data = [
        {
            'title': t.title,
            'description': t.description or '',
            'priority': t.priority,
            'category': t.category,
            'due_date': t.due_date.isoformat() if t.due_date else None,
            'completed': t.completed
        }
        for t in tasks
    ]
    resp = jsonify(tasks_data)
    resp.headers['Content-Disposition'] = 'attachment; filename="tasks.json"'
    resp.headers['Content-Type'] = 'application/json'
    return resp

@main_bp.post('/tasks/import')
@login_required
def import_tasks_route():
    try:
        from app.routes.api import extract_task_list, validate_and_parse_task_item
        items = extract_task_list(request)
        validated = [validate_and_parse_task_item(item, idx) for idx, item in enumerate(items)]
        for task_dict in validated:
            t = Task(
                user_id=current_user.id,
                title=task_dict['title'],
                description=task_dict['description'],
                priority=task_dict['priority'],
                category=task_dict['category'],
                due_date=task_dict['due_date'],
                completed=task_dict['completed']
            )
            db.session.add(t)
        db.session.commit()
        flash(f'Successfully imported {len(validated)} task(s).', 'success')
    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'error')
    except Exception:
        db.session.rollback()
        flash('Failed to import tasks.', 'error')
    return redirect(url_for('main.tasks'))

@main_bp.get('/deadlines')
@login_required
def deadlines(): return render_template('deadlines.html', tasks=Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc().nullslast()).all())


from app.models import TimetableEntry, DAYS_OF_WEEK
from app.services.timetable import parse_time_str, get_weekly_timetable, get_upcoming_classes

@main_bp.get('/timetable')
@login_required
def timetable():
    weekly_schedule = get_weekly_timetable(current_user)
    upcoming_classes = get_upcoming_classes(current_user)
    return render_template('timetable.html', schedule=weekly_schedule, upcoming=upcoming_classes, days=DAYS_OF_WEEK)

@main_bp.post('/timetable')
@login_required
def create_timetable():
    try:
        code = limited(request.form.get('course_code'), 30)
        name = limited(request.form.get('course_name'), 100)
        day = int(request.form.get('day_of_week', 0))
        start = parse_time_str(request.form.get('start_time'))
        end = parse_time_str(request.form.get('end_time'))
        if start >= end:
            raise ValueError('Start time must be before end time.')
        loc = limited(request.form.get('location', ''), 100, False)
        inst = limited(request.form.get('instructor', ''), 100, False)
        color = limited(request.form.get('color', '#3157d5'), 20, False)
        entry = TimetableEntry(user_id=current_user.id, course_code=code, course_name=name, day_of_week=day, start_time=start, end_time=end, location=loc, instructor=inst, color=color)
        db.session.add(entry)
        db.session.commit()
        flash(f'Added {code} to timetable.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('main.timetable'))

@main_bp.post('/timetable/<int:item_id>/delete')
@login_required
def delete_timetable(item_id):
    entry = TimetableEntry.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not entry:
        flash('Timetable entry not found.', 'error')
    else:
        db.session.delete(entry)
        db.session.commit()
        flash('Class removed from timetable.', 'success')
    return redirect(url_for('main.timetable'))


@main_bp.get('/notes')
@login_required
def notes(): return render_template('notes.html', notes=Note.query.filter_by(user_id=current_user.id).order_by(Note.updated_at.desc()).all())

@main_bp.get('/notes/<int:item_id>/export')
@login_required
def export_note_markdown(item_id):
    import re
    from flask import Response
    note = Note.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    clean_title = re.sub(r'[^a-zA-Z0-9_\- ]+', '', note.title).strip().replace(' ', '_') or f'note-{note.id}'
    filename = f"{clean_title}.md"
    body = f"# {note.title}\n\n**Subject:** {note.subject or 'General'}\n**Updated:** {note.updated_at.strftime('%Y-%m-%d')}\n\n---\n\n{note.content}\n"
    return Response(body, mimetype='text/markdown', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

@main_bp.get('/resources')
@login_required
def resources(): return render_template('resources.html', resources=Resource.query.order_by(Resource.created_at.desc()).all())

@main_bp.get('/announcements')
@login_required
def announcements(): return render_template('announcements.html', announcements=Announcement.query.order_by(Announcement.created_at.desc()).all())

@main_bp.get('/notifications')
@login_required
def notifications(): return render_template('notifications.html', notifications=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all())

@main_bp.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    if request.method=='POST':
        try:
            current_user.name=limited(request.form.get('name'),80); current_user.department=limited(request.form.get('department'),100,False); current_user.year=limited(request.form.get('year'),20,False)
            db.session.commit(); flash('Profile updated.', 'success')
        except ValueError as e: flash(str(e),'error')
    return render_template('profile.html')

@main_bp.get('/profile/export')
@login_required
def export_user_data():
    import json
    from flask import Response
    from app.services.account import export_user_account_data
    data = export_user_account_data(current_user)
    resp = Response(json.dumps(data, indent=2), mimetype='application/json')
    resp.headers['Content-Disposition'] = 'attachment; filename="campus_hub_data_export.json"'
    return resp

@main_bp.post('/profile/delete-account')
@login_required
def delete_account():
    from app.services.account import delete_user_account
    password = request.form.get('password', '')
    if not current_user.check_password(password):
        flash('Incorrect password. Account deletion aborted.', 'error')
        return redirect(url_for('main.profile'))
    user_to_delete = current_user._get_current_object()
    delete_user_account(user_to_delete)
    flash('Your account and all associated data have been permanently deleted.', 'info')
    return redirect(url_for('auth.login'))


from app.models import StudyGroup, StudyGroupMember, StudyGroupResource

@main_bp.route('/groups', methods=['GET', 'POST'])
@login_required
def groups():
    if request.method == 'POST':
        try:
            name = limited(request.form.get('name'), 100)
            desc = limited(request.form.get('description'), 2000, False)
            subject = limited(request.form.get('subject', 'General'), 100, False) or 'General'
            group = StudyGroup(name=name, description=desc, subject=subject, creator_id=current_user.id)
            db.session.add(group)
            db.session.flush()
            member = StudyGroupMember(group_id=group.id, user_id=current_user.id, role='creator')
            db.session.add(member)
            db.session.commit()
            flash('Study group created successfully!', 'success')
            return redirect(url_for('main.group_detail', group_id=group.id))
        except ValueError as e:
            flash(str(e), 'error')

    all_groups = StudyGroup.query.order_by(StudyGroup.created_at.desc()).all()
    my_groups = [g for g in all_groups if g.is_member(current_user.id)]
    return render_template('groups.html', groups=all_groups, my_groups=my_groups)

@main_bp.get('/groups/<int:group_id>')
@login_required
def group_detail(group_id):
    group = db.session.get(StudyGroup, group_id)
    if not group:
        flash('Study group not found.', 'error')
        return redirect(url_for('main.groups'))
    is_member = group.is_member(current_user.id)
    is_creator = group.creator_id == current_user.id or current_user.role == 'admin'
    return render_template('group_detail.html', group=group, is_member=is_member, is_creator=is_creator)

@main_bp.post('/groups/<int:group_id>/join')
@login_required
def join_group(group_id):
    group = db.session.get(StudyGroup, group_id)
    if not group:
        flash('Study group not found.', 'error')
        return redirect(url_for('main.groups'))
    if group.is_member(current_user.id):
        flash('You are already a member of this group.', 'info')
    else:
        member = StudyGroupMember(group_id=group.id, user_id=current_user.id, role='member')
        db.session.add(member)
        db.session.commit()
        flash(f'Joined {group.name}!', 'success')
    return redirect(url_for('main.group_detail', group_id=group.id))

@main_bp.post('/groups/<int:group_id>/leave')
@login_required
def leave_group(group_id):
    group = db.session.get(StudyGroup, group_id)
    if not group:
        flash('Study group not found.', 'error')
        return redirect(url_for('main.groups'))
    member = group.get_member(current_user.id)
    if not member:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('main.group_detail', group_id=group.id))

    if group.creator_id == current_user.id:
        other_members = [m for m in group.members if m.user_id != current_user.id]
        if other_members:
            next_leader = sorted(other_members, key=lambda m: m.joined_at)[0]
            next_leader.role = 'creator'
            group.creator_id = next_leader.user_id
            db.session.delete(member)
            db.session.commit()
            flash('You left the group. Leadership was transferred.', 'info')
            return redirect(url_for('main.groups'))
        else:
            db.session.delete(group)
            db.session.commit()
            flash('You left the group. As the last member, the group was disbanded.', 'info')
            return redirect(url_for('main.groups'))

    db.session.delete(member)
    db.session.commit()
    flash(f'Left {group.name}.', 'info')
    return redirect(url_for('main.groups'))

@main_bp.post('/groups/<int:group_id>/delete')
@login_required
def delete_group(group_id):
    group = db.session.get(StudyGroup, group_id)
    if not group:
        flash('Study group not found.', 'error')
        return redirect(url_for('main.groups'))
    if group.creator_id != current_user.id and current_user.role != 'admin':
        flash('Only group creator or admin can delete this group.', 'error')
        return redirect(url_for('main.group_detail', group_id=group.id))
    db.session.delete(group)
    db.session.commit()
    flash('Study group deleted.', 'success')
    return redirect(url_for('main.groups'))

@main_bp.post('/groups/<int:group_id>/resources')
@login_required
def add_group_resource(group_id):
    group = db.session.get(StudyGroup, group_id)
    if not group:
        flash('Study group not found.', 'error')
        return redirect(url_for('main.groups'))
    if not group.is_member(current_user.id) and current_user.role != 'admin':
        flash('Only group members can share resources.', 'error')
        return redirect(url_for('main.group_detail', group_id=group.id))
    try:
        title = limited(request.form.get('title'), 150)
        url = valid_url(request.form.get('url'))
        desc = limited(request.form.get('description'), 2000, False)
        rtype = request.form.get('resource_type', 'Other')
        res = StudyGroupResource(group_id=group.id, user_id=current_user.id, title=title, url=url, description=desc, resource_type=rtype)
        db.session.add(res)
        db.session.commit()
        flash('Resource shared with the group!', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('main.group_detail', group_id=group.id))

@main_bp.post('/groups/<int:group_id>/resources/<int:resource_id>/delete')
@login_required
def delete_group_resource(group_id, resource_id):
    group = db.session.get(StudyGroup, group_id)
    if not group:
        flash('Study group not found.', 'error')
        return redirect(url_for('main.groups'))
    res = db.session.get(StudyGroupResource, resource_id)
    if not res or res.group_id != group.id:
        flash('Resource not found.', 'error')
        return redirect(url_for('main.group_detail', group_id=group.id))
    if res.user_id != current_user.id and group.creator_id != current_user.id and current_user.role != 'admin':
        flash('Permission denied to delete this resource.', 'error')
        return redirect(url_for('main.group_detail', group_id=group.id))
    db.session.delete(res)
    db.session.commit()
    flash('Shared resource deleted.', 'success')
    return redirect(url_for('main.group_detail', group_id=group.id))

from app.models import StudySession
from app.services.study_planner import generate_study_schedule, save_study_schedule
@main_bp.get('/study-planner')
@login_required
def study_planner():
    daily_hours = float(request.args.get('daily_hours', 2.0))
    days_ahead = int(request.args.get('days_ahead', 7))
    plan = generate_study_schedule(current_user, daily_hours=daily_hours, days_ahead=days_ahead)
    saved_sessions = StudySession.query.filter_by(user_id=current_user.id).order_by(StudySession.planned_date.asc(), StudySession.id.asc()).all()
    return render_template('study_planner.html', plan=plan, saved_sessions=saved_sessions, daily_hours=daily_hours, days_ahead=days_ahead)

@main_bp.post('/study-planner/generate')
@login_required
def generate_planner():
    try:
        daily_hours = float(request.form.get('daily_hours', 2.0))
        days_ahead = int(request.form.get('days_ahead', 7))
        plan = generate_study_schedule(current_user, daily_hours=daily_hours, days_ahead=days_ahead)
        if request.form.get('save_plan') == 'true':
            save_study_schedule(current_user, plan)
            flash('Study schedule generated and saved to your plan!', 'success')
        else:
            flash('Study schedule generated.', 'info')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('main.study_planner', daily_hours=daily_hours, days_ahead=days_ahead))

@main_bp.post('/study-planner/sessions/<int:session_id>/toggle')
@login_required
def toggle_study_session(session_id):
    sess = StudySession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if sess:
        sess.completed = not sess.completed
        db.session.commit()
        flash('Session updated.', 'success')
    return redirect(url_for('main.study_planner'))

@main_bp.post('/study-planner/clear')
@login_required
def clear_study_planner():
    StudySession.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Saved study sessions cleared.', 'info')
    return redirect(url_for('main.study_planner'))
