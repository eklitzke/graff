import hashlib
from sqlalchemy import create_engine, Column
from sqlalchemy.types import Integer, String, Text, Float, DateTime, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from graff import config
from graff import crypto

engine = create_engine('mysql+mysqldb://' +
                       config.get('db_user', 'graff') + ':' +
                       config.get('db_pass', 'gr4ff') + '@' + 
                       config.get('db_host', '127.0.0.1') + '/' +
                       config.get('db_schema', 'graff'), pool_recycle=3600)
Session = sessionmaker(bind=engine)

class _Base(object):

    @property
    def encid(self):
        if hasattr(self, 'key_secret'):
            return crypto.encid(self.id, self.key_secret)
        else:
            return crypto.encid(self.id)

    @classmethod
    def create(cls, session, **kw):
        obj = cls(**kw)
        session.add(obj)
        return obj

    @classmethod
    def from_encid(cls, session, encid):
        if hasattr(cls, 'key_secret'):
            row_id = crypto.decid(encid, cls.key_secret)
        else:
            row_id = crypto.decid(encid)
        return session.query(cls).filter(cls.id == row_id).first()

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
    photo_time = Column(DateTime)
    photo_height = Column(Integer, nullable=False)
    photo_width = Column(Integer, nullable=False)
    sensor = Column(Boolean)
    time_created = Column(DateTime, nullable=False)

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    pw_hash = Column(String(56), nullable=False)
    email = Column(String)
    location = Column(String)
    time_created = Column(DateTime, nullable=False)

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
        return super(User, cls).create(session, **kwargs)

    @classmethod
    def authenticate(cls, session, name, password):
        row = session.query(cls).filter(cls.name == name).first()
        if row is None:
            return None
        row_hash = row.pw_hash.decode('hex')
        if hashlib.sha1(str(row_hash[:8]) + password.encode('ascii')).digest() == row_hash[8:]:
            return row
        return None