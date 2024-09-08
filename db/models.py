import pymysql
pymysql.install_as_MySQLdb()

from sqlalchemy import create_engine, Column, Table, Integer, Boolean, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
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
    item_id = Column(Integer, ForeignKey('items.item_id'), index=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), index=True, nullable=False)
    date_added = Column(DateTime, index=True)
    npc_id = Column(Integer, ForeignKey('npc_list.npc_id'), index=True)
    date_updated = Column(DateTime, onupdate=func.now())
    value = Column(Integer)
    quantity = Column(Integer)
    partition = Column(Integer, default=get_current_partition, index=True)
    
    player = relationship("Player", back_populates="drops")
    notified_drops = relationship("NotifiedDrop", back_populates="drop")

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
    entry_id = Column(Integer, autoincrement=True, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), nullable=False)
    npc_name = Column(String(35), ForeignKey('npc_list.npc_name'), nullable=False)
    total_loot = Column(String(50), nullable=False, default=0)
    last_updated = Column(DateTime, onupdate=func.now())
    
    player = relationship("Player", back_populates="player_totals")
    npc = relationship("NpcList")

class NpcList(Base):
    """
        Stores the list of valid NPCs that are 
        being tracked individually for ranking purposes
    """
    __tablename__ = 'npc_list'
    npc_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    npc_name = Column(String(60), nullable=False)

class ItemList(Base):
    __tablename__ = 'items'
    item_id = Column(Integer, primary_key=True,nullable=False, index=True)
    item_name = Column(String(125), index=True)
    noted = Column(Boolean, nullable=False)

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
    player_totals = relationship("PlayerTotal", back_populates="player")

    def __init__(self, wom_id, player_name, user_id=None, user=None, log_slots=0, total_level=0):
        self.wom_id = wom_id
        self.player_name = player_name
        self.user_id = user_id
        self.user = user
        self.log_slots = log_slots
        self.total_level = total_level

class User(Base):
    """
        :param: discord_id: The string formatted representation of the user's Discord ID
        :param: username: The user's Discord display name
        :param: patreon: The patreon subscription status of the user
    """
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String(35))
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())
    username = Column(String(20))
    patreon = Column(Boolean, default=False)
    players = relationship("Player", back_populates="user")
    groups = relationship("Group", secondary=user_group_association, back_populates="users", overlaps="groups")


class Group(Base):
    """
    :param: group_name: Publicly-displayed name of the group
    :param: wom_id: WiseOldMan group ID associated with the Group
    :param: guild_id: Discord Guild ID, if one is associated with it"""
    __tablename__ = 'groups'
    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(30), index=True)
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())
    wom_id = Column(Integer, default=None)
    guild_id = Column(String(255), default=None, nullable=True)
    
    configurations = relationship("GroupConfiguration", back_populates="group")
    # drops = relationship("Drop", back_populates="group")
    players = relationship("Player", secondary=user_group_association, back_populates="groups", overlaps="groups")
    users = relationship("User", secondary=user_group_association, back_populates="groups", overlaps="groups,players")

class GroupConfiguration(Base):
    __tablename__ = 'group_configurations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), nullable=False)
    config_key = Column(String(60), nullable=False)
    config_value = Column(String(255), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    group = relationship("Group", back_populates="configurations")

class Guild(Base):
    """ 
    :param: guild_id: Discord guild_id, string-formatted.
    :param: group_id: Respective group_id, if one already exists
    :param: date_added: Time the guild was generated
    :param: initialized: Status of the guild's registration (do they have a Group associated?)
        Guilds are stored in the database on the bot's invitiation to the server.
        They are used relationally to help convert a group to a discord guild. 
    """
    __tablename__ = 'guilds'
    guild_id = Column(String(255), primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.group_id'), nullable=True)
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())
    initialized = Column(Boolean, default=False)

class Webhook(Base):
    __tablename__ = 'webhooks'
    webhook_id = Column(Integer, primary_key=True)
    webhook_url = Column(String(255), unique=True)
    date_added = Column(DateTime)
    date_updated = Column(DateTime, onupdate=func.now())


# Setup database connection and create tables
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost:3306/data', pool_size=20, max_overflow=10)
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine))
session = Session()
