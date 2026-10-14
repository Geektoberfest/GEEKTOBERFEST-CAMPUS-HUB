from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_
from app.extensions import db
from app.models import Task, Note, Resource, Announcement, Notification
from app.utils.validation import clean, limited, valid_url
from app.services.dashboard import dashboard_stats

api_bp=Blueprint('api',__name__,url_prefix='/api')

def ok(data=None,status=200): return jsonify({'success':True,'data':data}),status
def err(message,status=400): return jsonify({'success':False,'error':message}),status

def parse_date(value):
    if not value: return None
    try: return datetime.strptime(value,'%Y-%m-%d').date()
    except ValueError: raise ValueError('Date must use YYYY-MM-DD.')

def task_json(t): return {'id':t.id,'title':t.title,'description':t.description,'priority':t.priority,'category':t.category,'due_date':t.due_date.isoformat() if t.due_date else None,'completed':t.completed}
def note_json(n): return {'id':n.id,'title':n.title,'content':n.content,'subject':n.subject,'created_at':n.created_at.isoformat(),'updated_at':n.updated_at.isoformat()}
def resource_json(r): return {'id':r.id,'title':r.title,'description':r.description,'subject':r.subject,'resource_type':r.resource_type,'url':r.url}
def announcement_json(a): return {'id':a.id,'title':a.title,'content':a.content,'category':a.category,'priority':a.priority,'created_at':a.created_at.isoformat()}

@api_bp.post('/auth/register')
def register_api():
    from app.models import User
    from app.utils.validation import valid_email,password_ok
    d=request.get_json(silent=True) or {}
    email=clean(d.get('email','')).lower(); password=d.get('password',''); name=clean(d.get('name',''))
    if len(name)<2 or not valid_email(email) or not password_ok(password): return err('Name, valid email and 8+ character password are required.')
    if User.query.filter_by(email=email).first(): return err('Email already registered.',409)
    u=User(name=name,email=email,role='student',department=clean(d.get('department','')),year=clean(d.get('year',''))); u.set_password(password); db.session.add(u); db.session.commit(); return ok({'id':u.id,'name':u.name},201)

@api_bp.get('/tasks')
@login_required
def get_tasks():
    q=clean(request.args.get('search','')).lower(); status=request.args.get('status','all'); priority=request.args.get('priority','all'); category=request.args.get('category','all')
    query=Task.query.filter_by(user_id=current_user.id)
    if q: query=query.filter(Task.title.ilike(f'%{q}%'))
    if status=='pending': query=query.filter_by(completed=False)
    if status=='completed': query=query.filter_by(completed=True)
    if priority!='all': query=query.filter_by(priority=priority)
    if category!='all': query=query.filter_by(category=category)
    return ok([task_json(t) for t in query.order_by(Task.due_date.asc().nullslast()).all()])

@api_bp.post('/tasks')
@login_required
def create_task():
    d=request.get_json(silent=True) or {}
    try:
        t=Task(user_id=current_user.id,title=limited(d.get('title'),150),description=limited(d.get('description'),2000,False),priority=d.get('priority','medium'),category=d.get('category','other'),due_date=parse_date(d.get('due_date')))
        if t.priority not in {'low','medium','high'} or t.category not in {'assignment','exam','project','personal','other'}: return err('Invalid task priority or category.')
        db.session.add(t); db.session.commit(); return ok(task_json(t),201)
    except ValueError as e: return err(str(e))

@api_bp.put('/tasks/<int:item_id>')
@login_required
def update_task(item_id):
    t=Task.query.filter_by(id=item_id,user_id=current_user.id).first()
    if not t: return err('Task not found.',404)
    d=request.get_json(silent=True) or {}
    try:
        if 'title' in d:t.title=limited(d['title'],150)
        if 'description' in d:t.description=limited(d['description'],2000,False)
        if 'priority' in d and d['priority'] in {'low','medium','high'}:t.priority=d['priority']
        if 'category' in d and d['category'] in {'assignment','exam','project','personal','other'}:t.category=d['category']
        if 'due_date' in d:t.due_date=parse_date(d['due_date'])
        if 'completed' in d:t.completed=bool(d['completed'])
        db.session.commit(); return ok(task_json(t))
    except ValueError as e:return err(str(e))

@api_bp.post('/tasks/<int:item_id>/duplicate')
@login_required
def duplicate_task(item_id):
    t=Task.query.filter_by(id=item_id,user_id=current_user.id).first()
    if not t: return err('Task not found.',404)
    copy_title = f"{t.title} (Copy)" if len(f"{t.title} (Copy)") <= 150 else t.title
    dup=Task(user_id=current_user.id,title=copy_title,description=t.description,priority=t.priority,category=t.category,due_date=t.due_date,completed=False)
    db.session.add(dup); db.session.commit(); return ok(task_json(dup),201)

@api_bp.delete('/tasks/<int:item_id>')
@login_required
def delete_task(item_id):
    t=Task.query.filter_by(id=item_id,user_id=current_user.id).first()
    if not t:return err('Task not found.',404)
    db.session.delete(t);db.session.commit();return ok()

def validate_and_parse_task_item(item, index=0):
    if not isinstance(item, dict):
        raise ValueError(f"Task at index {index} must be a JSON object.")
    title = item.get('title')
    if not title or not isinstance(title, str) or not title.strip():
        raise ValueError(f"Task at index {index} is missing a title.")
    clean_title = limited(title.strip(), 150)
    raw_desc = item.get('description', '')
    if raw_desc is not None and not isinstance(raw_desc, str):
        raise ValueError(f"Task at index {index} description must be a string.")
    clean_desc = limited(raw_desc or '', 2000, False)
    priority = item.get('priority', 'medium')
    if priority not in {'low', 'medium', 'high'}:
        raise ValueError(f"Task at index {index} has invalid priority: '{priority}'.")
    category = item.get('category', 'other')
    if category not in {'assignment', 'exam', 'project', 'personal', 'other'}:
        raise ValueError(f"Task at index {index} has invalid category: '{category}'.")
    raw_due = item.get('due_date')
    due_date = None
    if raw_due:
        try:
            due_date = parse_date(raw_due)
        except ValueError:
            raise ValueError(f"Task at index {index} has invalid due date format (expected YYYY-MM-DD).")
    completed = bool(item.get('completed', False))
    return {
        'title': clean_title,
        'description': clean_desc,
        'priority': priority,
        'category': category,
        'due_date': due_date,
        'completed': completed
    }

def extract_task_list(req):
    import json
    if 'file' in req.files:
        f = req.files['file']
        if not f.filename:
            raise ValueError('No file selected.')
        try:
            raw = json.load(f)
        except Exception:
            raise ValueError('Uploaded file is not valid JSON.')
    else:
        raw = req.get_json(silent=True)
        if raw is None:
            raise ValueError('Invalid JSON payload.')
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict) and 'tasks' in raw and isinstance(raw['tasks'], list):
        items = raw['tasks']
    elif isinstance(raw, dict) and 'data' in raw and isinstance(raw['data'], list):
        items = raw['data']
    else:
        raise ValueError('Expected a JSON list of tasks or an object with a tasks array.')
    if not items:
        raise ValueError('No tasks found to import.')
    return items

@api_bp.get('/tasks/export')
@login_required
def export_tasks():
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
    resp = jsonify({'success': True, 'data': tasks_data, 'tasks': tasks_data})
    resp.headers['Content-Disposition'] = 'attachment; filename="tasks.json"'
    return resp

@api_bp.post('/tasks/import')
@login_required
def import_tasks():
    try:
        items = extract_task_list(request)
        validated = [validate_and_parse_task_item(item, idx) for idx, item in enumerate(items)]
        created = []
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
            created.append(t)
        db.session.commit()
        return ok({'imported_count': len(created), 'tasks': [task_json(t) for t in created]}, 201)
    except ValueError as e:
        db.session.rollback()
        return err(str(e), 400)
    except Exception:
        db.session.rollback()
        return err('Failed to import tasks.', 500)

@api_bp.get('/notes')
@login_required
def get_notes():
    q=clean(request.args.get('search','')).lower(); query=Note.query.filter_by(user_id=current_user.id)
    if q:query=query.filter(or_(Note.title.ilike(f'%{q}%'),Note.content.ilike(f'%{q}%')))
    return ok([note_json(n) for n in query.order_by(Note.updated_at.desc()).all()])

@api_bp.post('/notes')
@login_required
def create_note():
    d=request.get_json(silent=True) or {}
    try:n=Note(user_id=current_user.id,title=limited(d.get('title'),150),content=limited(d.get('content'),10000),subject=limited(d.get('subject'),100,False));db.session.add(n);db.session.commit();return ok(note_json(n),201)
    except ValueError as e:return err(str(e))

@api_bp.put('/notes/<int:item_id>')
@login_required
def update_note(item_id):
    n=Note.query.filter_by(id=item_id,user_id=current_user.id).first()
    if not n:return err('Note not found.',404)
    d=request.get_json(silent=True) or {}
    try:n.title=limited(d.get('title',n.title),150);n.content=limited(d.get('content',n.content),10000);n.subject=limited(d.get('subject',n.subject),100,False);db.session.commit();return ok(note_json(n))
    except ValueError as e:return err(str(e))

@api_bp.delete('/notes/<int:item_id>')
@login_required
def delete_note(item_id):
    n=Note.query.filter_by(id=item_id,user_id=current_user.id).first()
    if not n:return err('Note not found.',404)
    db.session.delete(n);db.session.commit();return ok()


from app.models import TimetableEntry, DAYS_OF_WEEK
from app.services.timetable import parse_time_str, get_upcoming_classes

@api_bp.get('/timetable')
@login_required
def get_timetable():
    day = request.args.get('day')
    query = TimetableEntry.query.filter_by(user_id=current_user.id)
    if day is not None and day != '':
        try:
            day_int = int(day)
            query = query.filter_by(day_of_week=day_int)
        except ValueError:
            pass
    entries = query.order_by(TimetableEntry.day_of_week.asc(), TimetableEntry.start_time.asc()).all()
    return ok([e.to_dict() for e in entries])

@api_bp.get('/timetable/upcoming')
@login_required
def get_upcoming_timetable():
    upcoming = get_upcoming_classes(current_user)
    return ok([{
        'id': u['entry'].id,
        'course_code': u['entry'].course_code,
        'course_name': u['entry'].course_name,
        'day_name': u['day_name'],
        'start_time': u['entry'].start_time.strftime('%H:%M'),
        'end_time': u['entry'].end_time.strftime('%H:%M'),
        'location': u['entry'].location,
        'instructor': u['entry'].instructor,
        'color': u['entry'].color,
        'is_today': u['is_today'],
        'is_ongoing': u['is_ongoing']
    } for u in upcoming])

@api_bp.post('/timetable')
@login_required
def create_timetable_entry():
    d = request.get_json(silent=True) or {}
    try:
        code = limited(d.get('course_code'), 30)
        name = limited(d.get('course_name'), 100)
        day = int(d.get('day_of_week', 0))
        if not (0 <= day <= 6):
            return err('day_of_week must be between 0 (Monday) and 6 (Sunday).')
        start = parse_time_str(d.get('start_time'))
        end = parse_time_str(d.get('end_time'))
        if start >= end:
            return err('Start time must be before end time.')
        loc = limited(d.get('location', ''), 100, False)
        inst = limited(d.get('instructor', ''), 100, False)
        color = limited(d.get('color', '#3157d5'), 20, False)
        entry = TimetableEntry(user_id=current_user.id, course_code=code, course_name=name, day_of_week=day, start_time=start, end_time=end, location=loc, instructor=inst, color=color)
        db.session.add(entry)
        db.session.commit()
        return ok(entry.to_dict(), 201)
    except ValueError as e:
        return err(str(e))

@api_bp.put('/timetable/<int:item_id>')
@login_required
def update_timetable_entry(item_id):
    entry = TimetableEntry.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not entry:
        return err('Timetable entry not found.', 404)
    d = request.get_json(silent=True) or {}
    try:
        if 'course_code' in d: entry.course_code = limited(d.get('course_code'), 30)
        if 'course_name' in d: entry.course_name = limited(d.get('course_name'), 100)
        if 'day_of_week' in d:
            day = int(d.get('day_of_week'))
            if not (0 <= day <= 6): return err('day_of_week must be between 0 and 6.')
            entry.day_of_week = day
        if 'start_time' in d: entry.start_time = parse_time_str(d.get('start_time'))
        if 'end_time' in d: entry.end_time = parse_time_str(d.get('end_time'))
        if entry.start_time >= entry.end_time:
            return err('Start time must be before end time.')
        if 'location' in d: entry.location = limited(d.get('location', ''), 100, False)
        if 'instructor' in d: entry.instructor = limited(d.get('instructor', ''), 100, False)
        if 'color' in d: entry.color = limited(d.get('color', '#3157d5'), 20, False)
        db.session.commit()
        return ok(entry.to_dict())
    except ValueError as e:
        return err(str(e))

@api_bp.delete('/timetable/<int:item_id>')
@login_required
def delete_timetable_entry(item_id):
    entry = TimetableEntry.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not entry:
        return err('Timetable entry not found.', 404)
    db.session.delete(entry)
    db.session.commit()
    return ok({'message': 'Timetable entry deleted successfully.'})


@api_bp.get('/resources')
@login_required
def get_resources():
    q=clean(request.args.get('search','')).lower(); subject=request.args.get('subject','all'); typ=request.args.get('type','all'); query=Resource.query
    if q:query=query.filter(or_(Resource.title.ilike(f'%{q}%'),Resource.description.ilike(f'%{q}%')))
    if subject!='all':query=query.filter_by(subject=subject)
    if typ!='all':query=query.filter_by(resource_type=typ)
    return ok([resource_json(r) for r in query.order_by(Resource.created_at.desc()).all()])

@api_bp.get('/announcements')
@login_required
def get_announcements():
    q=clean(request.args.get('search','')).lower(); category=request.args.get('category','all'); priority=request.args.get('priority','all'); query=Announcement.query
    if q:query=query.filter(or_(Announcement.title.ilike(f'%{q}%'),Announcement.content.ilike(f'%{q}%')))
    if category!='all':query=query.filter_by(category=category)
    if priority!='all':query=query.filter_by(priority=priority)
    return ok([announcement_json(a) for a in query.order_by(Announcement.created_at.desc()).all()])

@api_bp.get('/dashboard')
@login_required
def dashboard_api():
    period=request.args.get('period','7d')
    start_date=request.args.get('start_date')
    end_date=request.args.get('end_date')
    s=dashboard_stats(current_user,start_date=start_date,end_date=end_date,period=period)
    return ok({'total':s['total'],'completed':s['completed'],'pending':s['pending'],'productivity':s['productivity'],'daily':s['daily'],'period':s['period'],'period_completed':s['period_completed'],'start_date':s['start_date'],'end_date':s['end_date']})

@api_bp.get('/notifications')
@login_required
def get_notifications(): return ok([{'id':n.id,'title':n.title,'message':n.message,'kind':n.kind,'read':n.read} for n in Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()])

@api_bp.post('/notifications/<int:item_id>/read')
@login_required
def read_notification(item_id):
    n=Notification.query.filter_by(id=item_id,user_id=current_user.id).first()
    if not n:return err('Notification not found.',404)
    n.read=True;db.session.commit();return ok()

@api_bp.post('/auth/login')
def login_api():
    from flask_login import login_user
    from app.models import User
    d=request.get_json(silent=True) or {}; email=clean(d.get('email','')).lower(); password=d.get('password','')
    u=User.query.filter_by(email=email).first()
    if not u or not u.check_password(password): return err('Invalid email or password.',401)
    login_user(u); return ok({'id':u.id,'name':u.name,'role':u.role})

@api_bp.post('/auth/logout')
@login_required
def logout_api():
    from flask_login import logout_user
    logout_user(); return ok()

@api_bp.get('/user/export')
@login_required
def export_user_data_api():
    from app.services.account import export_user_account_data
    return ok(export_user_account_data(current_user))

@api_bp.route('/user/account', methods=['DELETE', 'POST'])
@login_required
def delete_user_account_api():
    from app.services.account import delete_user_account
    d = request.get_json(silent=True) or request.form.to_dict() or {}
    password = d.get('password', '')
    if not current_user.check_password(password):
        return err('Incorrect password. Account deletion aborted.', 400)
    user_to_delete = current_user._get_current_object()
    delete_user_account(user_to_delete)
    return ok({'message': 'Account and all associated records deleted successfully.'})


from app.models import StudyGroup, StudyGroupMember, StudyGroupResource

def group_json(g, user_id=None):
    res = {
        'id': g.id,
        'name': g.name,
        'description': g.description,
        'subject': g.subject,
        'creator_id': g.creator_id,
        'member_count': len(g.members),
        'created_at': g.created_at.isoformat(),
        'updated_at': g.updated_at.isoformat(),
        'members': [{'user_id': m.user_id, 'name': m.user.name, 'role': m.role, 'joined_at': m.joined_at.isoformat()} for m in g.members]
    }
    if user_id:
        res['is_member'] = g.is_member(user_id)
        res['is_creator'] = g.creator_id == user_id
    return res

def group_resource_json(r):
    return {
        'id': r.id,
        'group_id': r.group_id,
        'user_id': r.user_id,
        'user_name': r.user.name if r.user else 'Unknown',
        'title': r.title,
        'url': r.url,
        'description': r.description,
        'resource_type': r.resource_type,
        'created_at': r.created_at.isoformat()
    }

@api_bp.post('/groups')
@login_required
def create_study_group_api():
    d = request.get_json(silent=True) or {}
    try:
        name = limited(d.get('name'), 100)
        desc = limited(d.get('description', ''), 2000, False)
        subject = limited(d.get('subject', 'General'), 100, False) or 'General'
        group = StudyGroup(name=name, description=desc, subject=subject, creator_id=current_user.id)
        db.session.add(group)
        db.session.flush()
        member = StudyGroupMember(group_id=group.id, user_id=current_user.id, role='creator')
        db.session.add(member)
        db.session.commit()
        return ok(group_json(group, current_user.id), 201)
    except ValueError as e:
        return err(str(e))

@api_bp.get('/groups')
@login_required
def list_study_groups_api():
    q = clean(request.args.get('search', '')).lower()
    mine = request.args.get('mine', '').lower() in ('true', '1')
    query = StudyGroup.query
    if q:
        query = query.filter(or_(StudyGroup.name.ilike(f'%{q}%'), StudyGroup.subject.ilike(f'%{q}%'), StudyGroup.description.ilike(f'%{q}%')))
    groups = query.order_by(StudyGroup.created_at.desc()).all()
    if mine:
        groups = [g for g in groups if g.is_member(current_user.id)]
    return ok([group_json(g, current_user.id) for g in groups])

@api_bp.get('/groups/<int:group_id>')
@login_required
def get_study_group_api(group_id):
    g = db.session.get(StudyGroup, group_id)
    if not g:
        return err('Study group not found.', 404)
    return ok(group_json(g, current_user.id))

@api_bp.delete('/groups/<int:group_id>')
@login_required
def delete_study_group_api(group_id):
    g = db.session.get(StudyGroup, group_id)
    if not g:
        return err('Study group not found.', 404)
    if g.creator_id != current_user.id and current_user.role != 'admin':
        return err('Permission denied. Only creator or admin can delete group.', 403)
    db.session.delete(g)
    db.session.commit()
    return ok({'message': 'Study group deleted successfully.'})

@api_bp.post('/groups/<int:group_id>/join')
@login_required
def join_study_group_api(group_id):
    g = db.session.get(StudyGroup, group_id)
    if not g:
        return err('Study group not found.', 404)
    if g.is_member(current_user.id):
        return err('Already a member of this study group.', 400)
    m = StudyGroupMember(group_id=g.id, user_id=current_user.id, role='member')
    db.session.add(m)
    db.session.commit()
    return ok(group_json(g, current_user.id))

@api_bp.post('/groups/<int:group_id>/leave')
@login_required
def leave_study_group_api(group_id):
    g = db.session.get(StudyGroup, group_id)
    if not g:
        return err('Study group not found.', 404)
    m = g.get_member(current_user.id)
    if not m:
        return err('Not a member of this study group.', 400)
    if g.creator_id == current_user.id:
        other_members = [mem for mem in g.members if mem.user_id != current_user.id]
        if other_members:
            next_leader = sorted(other_members, key=lambda x: x.joined_at)[0]
            next_leader.role = 'creator'
            g.creator_id = next_leader.user_id
            db.session.delete(m)
            db.session.commit()
            return ok({'message': 'Left study group. Leadership transferred.'})
        else:
            db.session.delete(g)
            db.session.commit()
            return ok({'message': 'Left study group. Group deleted because no members remain.'})
    db.session.delete(m)
    db.session.commit()
    return ok({'message': 'Left study group successfully.'})

@api_bp.get('/groups/<int:group_id>/resources')
@login_required
def list_group_resources_api(group_id):
    g = db.session.get(StudyGroup, group_id)
    if not g:
        return err('Study group not found.', 404)
    if not g.is_member(current_user.id) and current_user.role != 'admin':
        return err('Must be a group member to view resources.', 403)
    resources = StudyGroupResource.query.filter_by(group_id=g.id).order_by(StudyGroupResource.created_at.desc()).all()
    return ok([group_resource_json(r) for r in resources])

@api_bp.post('/groups/<int:group_id>/resources')
@login_required
def add_group_resource_api(group_id):
    g = db.session.get(StudyGroup, group_id)
    if not g:
        return err('Study group not found.', 404)
    if not g.is_member(current_user.id) and current_user.role != 'admin':
        return err('Must be a group member to share resources.', 403)
    d = request.get_json(silent=True) or {}
    try:
        title = limited(d.get('title'), 150)
        url = valid_url(d.get('url'))
        desc = limited(d.get('description', ''), 2000, False)
        rtype = d.get('resource_type', 'Other')
        res = StudyGroupResource(group_id=g.id, user_id=current_user.id, title=title, url=url, description=desc, resource_type=rtype)
        db.session.add(res)
        db.session.commit()
        return ok(group_resource_json(res), 201)
    except ValueError as e:
        return err(str(e))

@api_bp.delete('/groups/<int:group_id>/resources/<int:resource_id>')
@login_required
def delete_group_resource_api(group_id, resource_id):
    g = db.session.get(StudyGroup, group_id)
    if not g:
        return err('Study group not found.', 404)
    r = db.session.get(StudyGroupResource, resource_id)
    if not r or r.group_id != g.id:
        return err('Resource not found.', 404)
    if r.user_id != current_user.id and g.creator_id != current_user.id and current_user.role != 'admin':
        return err('Permission denied to delete this resource.', 403)
    db.session.delete(r)
    db.session.commit()
    return ok({'message': 'Resource deleted successfully.'})

@api_bp.get('/translations')
def get_translations_api():
    from app.services.i18n import get_current_language, get_translations_for_client, SUPPORTED_LANGUAGES
    lang = request.args.get('lang') or get_current_language()
    catalog = get_translations_for_client(lang)
    return ok({
        'language': lang,
        'supported_languages': SUPPORTED_LANGUAGES,
        'translations': catalog
    })

@api_bp.put('/user/language')
@login_required
def set_user_language_api():
    from app.services.i18n import SUPPORTED_LANGUAGES
    d = request.get_json(silent=True) or {}
    lang = d.get('language')
    if not lang or lang not in SUPPORTED_LANGUAGES:
        return err(f"Invalid language. Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}")
    current_user.language = lang
    db.session.commit()
    return ok({'language': lang})
