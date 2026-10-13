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

@api_bp.delete('/tasks/<int:item_id>')
@login_required
def delete_task(item_id):
    t=Task.query.filter_by(id=item_id,user_id=current_user.id).first()
    if not t:return err('Task not found.',404)
    db.session.delete(t);db.session.commit();return ok()

@api_bp.post('/tasks/bulk')
@login_required
def bulk_tasks():
    d=request.get_json(silent=True) or {}
    action=d.get('action','')
    ids=d.get('ids',[])
    if action not in {'complete_all','incomplete_all','delete_all'}: return err('Invalid action. Use complete_all, incomplete_all, or delete_all.')
    if not isinstance(ids,list) or not ids: return err('ids must be a non-empty list of task IDs.')
    if len(ids)>200: return err('Cannot act on more than 200 tasks at once.')
    tasks=Task.query.filter(Task.id.in_(ids),Task.user_id==current_user.id).all()
    if not tasks: return err('No matching tasks found.',404)
    if action=='delete_all':
        for t in tasks: db.session.delete(t)
    else:
        completed=(action=='complete_all')
        for t in tasks: t.completed=completed
    db.session.commit()
    return ok({'affected':len(tasks)})

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
    s=dashboard_stats(current_user); return ok({'total':s['total'],'completed':s['completed'],'pending':s['pending'],'productivity':s['productivity'],'daily':s['daily']})

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
