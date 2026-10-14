from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    department = db.Column(db.String(100), default='')
    year = db.Column(db.String(20), default='')
    avatar = db.Column(db.String(255), default='')
    joined_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    tasks = db.relationship('Task', backref='owner', lazy=True, cascade='all, delete-orphan')
    notes = db.relationship('Note', backref='owner', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default='')
    priority = db.Column(db.String(20), nullable=False, default='medium')
    category = db.Column(db.String(30), nullable=False, default='other')
    recurrence = db.Column(db.String(20), nullable=False, default='none')
    due_date = db.Column(db.Date, nullable=True, index=True)
    completed = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    subject = db.Column(db.String(100), default='General')
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


class TimetableEntry(db.Model):
    __tablename__ = 'timetable_entries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    course_code = db.Column(db.String(30), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(100), default='')
    instructor = db.Column(db.String(100), default='')
    color = db.Column(db.String(20), default='#3157d5')
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('timetable_entries', lazy=True, cascade='all, delete-orphan'))

    @property
    def day_name(self):
        if 0 <= self.day_of_week < len(DAYS_OF_WEEK):
            return DAYS_OF_WEEK[self.day_of_week]
        return 'Unknown'

    def to_dict(self):
        return {
            'id': self.id,
            'course_code': self.course_code,
            'course_name': self.course_name,
            'day_of_week': self.day_of_week,
            'day_name': self.day_name,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else '',
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else '',
            'location': self.location,
            'instructor': self.instructor,
            'color': self.color
        }


class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default='')
    subject = db.Column(db.String(100), default='General')
    resource_type = db.Column(db.String(30), nullable=False, default='Other')
    url = db.Column(db.String(500), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, default='General')
    priority = db.Column(db.String(20), nullable=False, default='Normal')
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    kind = db.Column(db.String(30), default='info')
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class StudyGroup(db.Model):
    __tablename__ = 'study_groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    subject = db.Column(db.String(100), default='General')
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    creator = db.relationship('User', backref='created_groups', foreign_keys=[creator_id])
    members = db.relationship('StudyGroupMember', backref='group', cascade='all, delete-orphan', lazy=True)
    resources = db.relationship('StudyGroupResource', backref='group', cascade='all, delete-orphan', lazy=True)

    def is_member(self, user_id):
        return any(m.user_id == user_id for m in self.members)

    def get_member(self, user_id):
        for m in self.members:
            if m.user_id == user_id:
                return m
        return None


class StudyGroupMember(db.Model):
    __tablename__ = 'study_group_members'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('study_groups.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role = db.Column(db.String(20), default='member', nullable=False)
    joined_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship('User', backref='group_memberships')

    __table_args__ = (db.UniqueConstraint('group_id', 'user_id', name='uq_group_user'),)


class StudyGroupResource(db.Model):
    __tablename__ = 'study_group_resources'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('study_groups.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, default='')
    resource_type = db.Column(db.String(30), default='Other', nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship('User', backref='shared_group_resources')
