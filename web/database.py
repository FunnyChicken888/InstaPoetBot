from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'instapoetbot.db'))
engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class PostHistory(Base):
    __tablename__ = 'post_history'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    image_filename = Column(String(500), default='')
    category = Column(String(100), default='')
    image_url = Column(String(1000), default='')
    caption = Column(Text, default='')
    instagram_post_id = Column(String(200), default='')
    status = Column(String(50))
    error_message = Column(Text, nullable=True)


def init_db():
    Base.metadata.create_all(engine)
