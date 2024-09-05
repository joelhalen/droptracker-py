import pymysql
pymysql.install_as_MySQLdb()

from sqlalchemy import create_engine, Column, Table, Integer, Boolean, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func
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
    item_name = Column(String(35))
    item_id = Column(Integer)
    player_id = Column(Integer, ForeignKey('players.player_id'), index=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), index=True, nullable=True)
    date_added = Column(DateTime, index=True)
    npc_name = Column(String(35), index=True)
    date_updated = Column(DateTime, onupdate=func.now())
    value = Column(Integer)
    quantity = Column(Integer)
    partition = Column(Integer, default=get_current_partition, index=True)
    
    player = relationship("Player", back_populates="drops")
    group = relationship("Group", back_populates="drops")

class NotifiedDrop(Base):
    """
        Drops that have exceeded the necessary threshold to have a notification
        sent to a Discord channel are stored in this table to allow modifications
        to be made to the message, drop, etc.
    """
    __tablename__ = 'notified_drops'
    notified_drop_id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String(35))
    message_id = Column(String(35))
    status = Column(String(15)) ## 'sent', 'removed' or 'pending'
    drop_id = Column(Integer, ForeignKey('drops.drop_id'), nullable=False)

    drop = relationship("Drop", back_populates="notified_drops")  

class PlayerTotal(Base):
    """
        Contains players' calculated totals and the last time they were updated
    """
    __tablename__ = 'player_totals'
    
    player_id = Column(Integer, ForeignKey('players.player_id'), nullable=False)
    npc_name = Column(String(35), ForeignKey('npc_list.npc_name'), nullable=False)
    total_loot = Column(String(50), nullable=False, default=0)
    last_updated = Column(DateTime, onupdate=func.now())
    
    player = relationship("Player", back_populates="player_totals")
    npc = relationship("NpcList", back_populates="player_totals")

class NpcList(Base):
    """
        Stores the list of valid NPCs that are 
        being tracked individually for ranking purposes
    """
    __tablename__ = 'npc_list'
    npc_name = Column(String(35), primary_key=True, nullable=False)


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
"""
    Redis defs:
    -- Note: Stored without the {} brackets, ofc.
    - Player drop keys:
        Monthly:
            All:
                pid_drops_mo_{pid}_all_{partition}
            Specific NPC:
                pid_drops_mo_{pid}_{npc_name}_{partition}
        All-time (patreon):
            All:
                pid_drops_at_{pid}_all
            Specific NPC:
                pid_drops_at_{pid}_{npc_name}
    - Group drop keys:
        Monthly:
            All:
                gid_drops_mo_{gid}_all_{partition}
            Specific NPC:
                gid_drops_mo_{gid}_{npc_name}_{partition}
        All-time (patreon):
            All:
                gid_drops_at_{pid}_all
            Specific NPC:
                gid_drops_at_{pid}_{npc_name}
"""
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
    player_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
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

    def __init__(self, wom_id, player_name, user_id=None, user=None, log_slots=0, total_level=0):
        self.wom_id = wom_id
        self.player_name = player_name
        self.user_id = user_id
        self.user = user
        self.log_slots = log_slots
        self.total_level = total_level

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String(25))
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())
    username = Column(String(20))
    patreon = Column(Boolean, default=False)
    players = relationship("Player", back_populates="user")
    groups = relationship("Group", secondary=user_group_association, back_populates="users", overlaps="groups")


class Group(Base):
    __tablename__ = 'groups'
    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(30), index=True)
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())
    wom_id = Column(Integer, default=None)
    guild_id = Column(Integer, default=None, nullable=True)
    
    configurations = relationship("GroupConfiguration", back_populates="group")
    drops = relationship("Drop", back_populates="group")
    players = relationship("Player", secondary=user_group_association, back_populates="groups", overlaps="groups")
    users = relationship("User", secondary=user_group_association, back_populates="groups", overlaps="groups,players")

class GroupConfiguration(Base):
    __tablename__ = 'group_configurations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), nullable=False)
    config_key = Column(String(20), nullable=False)
    config_value = Column(String(255), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    group = relationship("Group", back_populates="configurations")

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
