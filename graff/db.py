import datetime
import hashlib
import os
import re
from sqlalchemy import create_engine, func, Column, ForeignKey
from sqlalchemy.types import Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base
import warnings

from graff import config
from graff import crypto

if config.get('memory', True):
    engine = create_engine('sqlite:///:memory:')
    now = func.datetime()
else:
    engine = create_engine('mysql+mysqldb://' +
                           config.get('db_user', 'graff') + ':' +
                           config.get('db_pass', 'gr4ff') + '@' +
                           config.get('db_host', '127.0.0.1') + '/' +
                           config.get('db_schema', 'graff'), pool_recycle=3600)
    now = func.now()

Session = sessionmaker(bind=engine)

class _Base(object):

    @property
    def encid(self):
        if hasattr(self, 'secret_key'):
            return crypto.encid(self.id, self.secret_key)
        else:
            return crypto.encid(self.id)

    @classmethod
    def create(cls, session, **kw):
        obj = cls(**kw)
        session.add(obj)
        return obj

    @classmethod
    def by_id(cls, session, row_id):
        return session.query(cls).filter(cls.id == row_id).first()

    @classmethod
    def from_encid(cls, session, encid):
        if hasattr(cls, 'secret_key'):
            row_id = crypto.decid(encid, cls.secret_key)
        else:
            row_id = crypto.decid(encid)
        return cls.by_id(session, row_id)

    @classmethod
    def most_recent(cls, session, limit):
        return session.query(cls).order_by(cls.id.desc()).limit(limit)

Base = declarative_base(cls=_Base)

class Photo(Base):
    __tablename__ = 'photo'

    id = Column(Integer, primary_key=True)
    body_hash = Column(String(40), nullable=False)
    content_type = Column(String(64), nullable=False)
    fsid = Column(String(32), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    make = Column(String(128))
    model = Column(String(128))
    photo_time = Column(DateTime, nullable=False, default=now)
    photo_height = Column(Integer, nullable=False)
    photo_width = Column(Integer, nullable=False)
    remote_ip = Column(Integer, nullable=False)
    sensor = Column(Boolean)
    time_created = Column(DateTime, nullable=False, default=now)
    user_id = Column(Integer, ForeignKey('user.id'))

    user = relationship('User', backref=backref('photos', order_by=id))

    @property
    def time_ago(self):
        delta = datetime.datetime.now() - self.time_created
        if delta < datetime.timedelta(seconds=30):
            return 'a moment ago'
        elif delta < datetime.timedelta(seconds=120):
            return '1 minute ago'
        elif delta < datetime.timedelta(seconds=59 * 60):
            return '%d minutes ago' % (int(delta.total_seconds() / 60.0),)
        elif delta < datetime.timedelta(seconds=120 * 60):
            return '1 hour ago'
        elif delta < datetime.timedelta(seconds=24 * 60 * 60):
            return '%d hours ago' % (int(delta.total_seconds() / 3600.0),)
        elif delta < datetime.timedelta(seconds=2 * 86400):
            return '1 day ago'
        else:
            return '%d days ago' % (int(delta.total_seconds() / 84600.0),)

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    pw_hash = Column(String(56), nullable=False)
    email = Column(String)
    location = Column(String)
    signup_ip = Column(Integer, nullable=False)
    login_ip = Column(Integer, nullable=False)
    time_created = Column(DateTime, nullable=False, default=now)

    @classmethod
    def create(cls, session, **kwargs):
        if session.query(cls).filter(cls.name == kwargs['name']).first() is not None:
            return 'That username has already been taken'
        if kwargs['email'] and session.query(cls).filter(cls.email == kwargs['email']).first() is not None:
            return 'That email has already been registered'
        with open('/dev/random', 'rb') as devrandom:
            salt = devrandom.read(8)
        hashval = hashlib.sha1(salt + kwargs.pop('password').encode('ascii')).digest()
        kwargs['pw_hash'] = (salt + hashval).encode('hex')
        kwargs['signup_ip'] = kwargs['login_ip'] = kwargs.pop('remote_ip')
        return super(User, cls).create(session, **kwargs)

    @classmethod
    def authenticate(cls, session, name, password, remote_ip):
        row = session.query(cls).filter(cls.name == name).first()
        if row is None:
            return None
        row_hash = row.pw_hash.decode('hex')
        if hashlib.sha1(str(row_hash[:8]) + password.encode('ascii')).digest() == row_hash[8:]:
            row.login_ip = remote_ip
            return row
        return None

    @classmethod
    def by_name(cls, session, name):
        return session.query(cls).filter(cls.name == name).first()

# set up encryption keys
g = globals()
crypto_keys = set()
for k, v in g.items():
    find_key = False
    try:
        if issubclass(v, Base) and v is not Base:
            find_key = True
    except TypeError:
        continue
    if find_key:
        if 'secret_key' in v.__dict__:
            warnings.warn('static key set for %s' % (v,))
        elif config.get('key_' + v.__name__) is not None:
            v.secret_key = config.get('key_' + v.__name__)
        elif config.get('memory'):
            v.secret_key = os.urandom(16)
        else:
            v.secret_key = '?' * 16
        if v.secret_key in crypto_keys:
            warnings.warn('re-using crypto key for %s' % (v,))
        crypto_keys.add(v.secret_key)
del crypto_keys
del g

if config.get('memory', True):
    Base.metadata.create_all(engine)
