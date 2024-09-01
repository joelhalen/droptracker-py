import pymysql
pymysql.install_as_MySQLdb()

from sqlalchemy import create_engine, Column, Table, Integer, Boolean, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext import func
from utils.format import get_current_partition
from dotenv import load_dotenv
import os
load_dotenv()

Base = declarative_base()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")


""" Define associations between users and players """
user_group_association = Table(
    'user_group_association', Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('player_id', Integer, ForeignKey('players.player_id'), nullable=True),
    Column('user_id', Integer, ForeignKey('users.user_id'), nullable=True),
    Column('group_id', Integer, ForeignKey('groups.group_id'), nullable=False)
)


class Drop(Base):
    __tablename__ = 'drops'
    drop_id = Column(Integer, primary_key=True, autoincrement=True)
    item_name = Column(String(35), index=True)
    item_id = Column(Integer, index=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), index=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), index=True, nullable=True)
    date_added = Column(DateTime, index=True)
    npc_name = Column(String(35), index=True)
    date_updated = Column(DateTime, onupdate=func.now())
    value = Column(Integer)
    quantity = Column(Integer)
    partition = Column(DateTime, default=get_current_partition, index=True)
    
    player = relationship("Player", back_populates="drops")
    group = relationship("Group", back_populates="drops")

class CollectionLogEntry(Base):
    """ 
        Example of another data type we will store in the sql database
    """
    __tablename__ = 'collection'
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    item_name = Column(String(35), index=True)
    item_id = Column(Integer, index=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), index=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), index=True)
    reported_slots = Column(Integer)
    date_added = Column(DateTime, index=True)
    date_updated = Column(DateTime, onupdate=func.now())

class Player(Base):
    """ 
    :param: wom_id: The player's WiseOldMan ID
    :param: player_name: The DISPLAY NAME of the player, exactly as it appears
    :param: user_id: The ID of the associated User object, if one exists
    :param: log_slots: Stored number of collected log slots
    :param: total_level: Account total level based on the last update with WOM.
        Defines the player object, which is instantly created any time a unique username
        submits a new drop/etc, and their WiseOldMan user ID doesn't already exist in our database.
    """
    __tablename__ = 'players'
    player_id = Column(Integer, primary_key=True, autoincrement=True)
    wom_id = Column(Integer, unique=True)
    player_name = Column(String(20), index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    log_slots = Column(Integer)
    total_level = Column(Integer)
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())
    
    user = relationship("User", back_populates="players")
    drops = relationship("Drop", back_populates="player")
    groups = relationship("Group", secondary=user_group_association, back_populates="players")

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String(25))
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())
    username = Column(String(20))
    players = relationship("Player", back_populates="user")
    groups = relationship("Group", secondary=user_group_association, back_populates="users")


class Group(Base):
    __tablename__ = 'groups'
    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(30), index=True)
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())
    wom_id = Column(Integer, default=None)
    drops = relationship("Drop", back_populates="group")
    players = relationship("Player", secondary=user_group_association, back_populates="groups")
    users = relationship("User", secondary=user_group_association, back_populates="groups")


class Guild(Base):
    """ 
        Guilds are stored in the database on the bot's invitiation to the server.
        They are used relationally to help convert a group to a discord guild. 
    """
    __tablename__ = 'guilds'
    guild_id = Column(String(30), primary_key=True)
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())
    initialized = Column(Boolean, default=False)

# Setup database connection and create tables
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost:3306/data')  
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
