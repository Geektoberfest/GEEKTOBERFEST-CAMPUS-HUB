from datetime import date, timedelta
from app.extensions import db
from app.models import Task, StudySession


CATEGORY_BASE_HOURS = {
    'exam': 4.0,
    'project': 3.5,
    'assignment': 2.0,
    'personal': 1.5,
    'other': 1.5
}

PRIORITY_MULTIPLIER = {
    'high': 1.5,
    'medium': 1.0,
    'low': 0.75
}

PRIORITY_WEIGHTS = {
    'high': 3,
    'medium': 2,
    'low': 1
}


def estimate_task_hours(task):
    base = CATEGORY_BASE_HOURS.get(task.category.lower(), 2.0)
    multiplier = PRIORITY_MULTIPLIER.get(task.priority.lower(), 1.0)
    return round(base * multiplier, 1)


def generate_study_schedule(user, daily_hours=2.0, days_ahead=7):
    daily_hours = max(0.5, min(float(daily_hours), 12.0))
    days_ahead = max(1, min(int(days_ahead), 30))

    today = date.today()
    pending_tasks = Task.query.filter_by(user_id=user.id, completed=False).all()

    if not pending_tasks:
        return {
            'summary': {
                'daily_study_hours': daily_hours,
                'days_ahead': days_ahead,
                'total_planned_hours': 0,
                'total_tasks_scheduled': 0,
                'at_risk_tasks': []
            },
            'days': []
        }

    # Prepare tasks with required hours and urgency
    task_items = []
    for t in pending_tasks:
        req_hours = estimate_task_hours(t)
        p_weight = PRIORITY_WEIGHTS.get(t.priority.lower(), 2)
        if t.due_date:
            days_left = (t.due_date - today).days
            if days_left <= 0:
                urgency = 1000.0  # overdue or due today
            else:
                urgency = (p_weight * 20.0) / max(1, days_left)
        else:
            urgency = float(p_weight)

        task_items.append({
            'task': t,
            'req_hours': req_hours,
            'rem_hours': req_hours,
            'urgency': urgency,
            'allocated_hours': 0.0
        })

    # Sort tasks by urgency descending
    task_items.sort(key=lambda x: x['urgency'], reverse=True)

    # Schedule day by day
    schedule_days = []
    total_planned_hours = 0.0

    for day_idx in range(days_ahead):
        current_date = today + timedelta(days=day_idx)
        available_today = daily_hours
        day_sessions = []

        # Find eligible tasks for this day
        for item in task_items:
            if available_today <= 0.01:
                break
            if item['rem_hours'] <= 0.01:
                continue

            t = item['task']
            # If task has a deadline that passed before this date, skip
            if t.due_date and t.due_date < current_date:
                continue

            # Allocate in session blocks of 1.0 or 0.5 hours
            alloc = min(available_today, item['rem_hours'])
            if alloc < 0.5 and item['rem_hours'] >= 0.5:
                # Chunks under 30 mins are only allocated if that's all that's left
                alloc = min(available_today, 0.5)

            alloc = round(alloc, 1)
            if alloc <= 0:
                continue

            available_today -= alloc
            item['rem_hours'] -= alloc
            item['allocated_hours'] += alloc
            total_planned_hours += alloc

            focus_text = f"Study {t.category.title()} materials and prep"
            if t.category == 'exam':
                focus_text = "Review lecture slides, notes, and key concepts"
            elif t.category in ('project', 'assignment'):
                focus_text = "Work on problem sets, implementation, and exercises"

            day_sessions.append({
                'task_id': t.id,
                'task_title': t.title,
                'category': t.category,
                'priority': t.priority,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'duration_hours': alloc,
                'focus': focus_text
            })

        schedule_days.append({
            'date': current_date.isoformat(),
            'day_name': current_date.strftime('%A'),
            'total_hours': round(daily_hours - available_today, 1),
            'sessions': day_sessions
        })

    # At-risk checks
    at_risk = []
    for item in task_items:
        t = item['task']
        if t.due_date and (t.due_date - today).days <= days_ahead:
            if item['allocated_hours'] < item['req_hours']:
                shortfall = round(item['req_hours'] - item['allocated_hours'], 1)
                at_risk.append({
                    'task_id': t.id,
                    'title': t.title,
                    'due_date': t.due_date.isoformat(),
                    'required_hours': item['req_hours'],
                    'allocated_hours': item['allocated_hours'],
                    'shortfall_hours': shortfall,
                    'warning': f'"{t.title}" is due {t.due_date.strftime("%d %b")} and needs {item["req_hours"]}h, but only {item["allocated_hours"]}h could be scheduled.'
                })

    scheduled_tasks = {s['task_id'] for d in schedule_days for s in d['sessions']}

    return {
        'summary': {
            'daily_study_hours': daily_hours,
            'days_ahead': days_ahead,
            'total_planned_hours': round(total_planned_hours, 1),
            'total_tasks_scheduled': len(scheduled_tasks),
            'at_risk_tasks': at_risk
        },
        'days': schedule_days
    }


def save_study_schedule(user, schedule_data):
    # Remove existing uncompleted future sessions
    today = date.today()
    StudySession.query.filter(
        StudySession.user_id == user.id,
        StudySession.planned_date >= today,
        StudySession.completed == False
    ).delete()

    created_sessions = []
    for day_data in schedule_data.get('days', []):
        session_date = date.fromisoformat(day_data['date'])
        for s_data in day_data.get('sessions', []):
            sess = StudySession(
                user_id=user.id,
                task_id=s_data['task_id'],
                title=f"Study: {s_data['task_title']}",
                planned_date=session_date,
                duration_hours=s_data['duration_hours'],
                notes=s_data.get('focus', '')
            )
            db.session.add(sess)
            created_sessions.append(sess)

    db.session.commit()
    return created_sessions
