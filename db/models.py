## Model definitions for database interactions

import pymysql
pymysql.install_as_MySQLdb()

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os
load_dotenv()

Base = declarative_base()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

class Drop(Base):
    __tablename__ = 'drops'
    drop_id = Column(Integer, primary_key=True, autoincrement=True)
    item_name = Column(String(35), index=True)
    item_id = Column(Integer, index=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), index=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), index=True)
    date_received = Column(DateTime, index=True)
    date_updated = Column(DateTime)
    value = Column(Integer)
    quantity = Column(Integer)
    
    player = relationship("Player", back_populates="drops")
    group = relationship("Group", back_populates="drops")

class CollectionLogEntry(Base):
    """ 
        Example of another data type we could store in the sql database
    """
    __tablename__ = 'collection'
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    item_name = Column(String(35), index=True)
    item_id = Column(Integer, index=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), index=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), index=True)
    reported_slots = Column(Integer)
    date_received = Column(DateTime, index=True)
    date_updated = Column(DateTime)


class Player(Base):
    """ 
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
    date_updated = Column(DateTime)
    
    user = relationship("User", back_populates="players")
    drops = relationship("Drop", back_populates="player")

class User(Base):
    """ 
    :param: discord_id
        Defines a user, which is separate from a 'Player'
        Users refer to a Discord account that has registered in the DropTracker database.
        Thus, a single 'user' object can have ownership of many 'player' objects.
    """
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String(25))
    username = Column(String(20))
    players = relationship("Player", back_populates="user")

class Group(Base):
    """ 
        A "Group" is separate from a "Guild". 
        Groups constitute Guilds that have properly configured the bot
    """
    __tablename__ = 'groups'
    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(30), index=True)
    wom_id = Column(Integer, default=None)
    drops = relationship("Drop", back_populates="group")

class Guild(Base):
    """ 
        Guilds are stored in the database on the bot's invitiation to the server.
        They are used relationally to help convert a group to a discord guild. 
    """
    __tablename__ = 'guilds'
    guild_id = Column(String(30))

# Setup database connection and create tables
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost:3306/data')  
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
session = None