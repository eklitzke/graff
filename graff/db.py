from sqlalchemy import create_engine, Column
from sqlalchemy.types import Integer, String, Text, Float, DateTime
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
        return crypto.encid(self.id)

    @classmethod
    def insert(cls, session, **kw):
        obj = cls(**kw)
        session.add(obj)
        return obj

    @classmethod
    def from_encid(cls, session, encid):
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
    time_created = Column(DateTime, nullable=False)

    DISPLAY_WIDTH = 900

    def html_dimensions(self):
        if self.photo_width <= self.DISPLAY_WIDTH:
            return {'width': self.photo_width, 'height': self.photo_height}
        return {'width': self.DISPLAY_WIDTH, 'height': int(self.photo_height * self.DISPLAY_WIDTH / self.photo_width) }
