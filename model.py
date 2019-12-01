from peewee import CharField, ForeignKeyField, IntegerField, DateTimeField, BooleanField, Model
import os

from playhouse.db_url import connect

from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import UserMixin

database = connect(os.environ.get('DATABASE_URL', 'sqlite:///auction.db'))
# database.execute_sql('PRAGMA foreign_keys = ON;')  # needed for sqlite only


class BaseModel(Model):
    class Meta:
        database = database


class Team(BaseModel):
    """
        This class defines a team to bid on
    """
    team = CharField(max_length=30, unique=True)
    # region
    # seed
    # 1st round opponenet


class Auction(BaseModel):
    """
        This class defines the auction groups
    """
    auction_name = CharField(max_length=30, unique=True)
    code = CharField(max_length=30)
    current_team = ForeignKeyField(Team, null=True)
    complete = BooleanField(default=False)


class User(UserMixin, BaseModel):
    """
        This class defines Users
    """
    username = CharField(max_length=30, unique=True)
    first_name = CharField(max_length=30, unique=True)
    last_name = CharField(max_length=30, unique=True)
    email = CharField(max_length=64, unique=True)
    password_hash = CharField(max_length=128)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Auction_result(BaseModel):
    """
        This class contains all the teams sold, their buyers, and the price
    """
    auction = ForeignKeyField(Auction)
    team = ForeignKeyField(Team)
    buyer = ForeignKeyField(User)
    price = IntegerField()


class User_access(BaseModel):
    """
        This class defines the auctions to which users have access
    """
    user_in_auction = ForeignKeyField(User)
    auction = ForeignKeyField(Auction)


class Bid(BaseModel):
    """
        This class defines bids that people make on teams
    """
    participant = ForeignKeyField(User)
    team_bid = ForeignKeyField(Team)
    bid_amount = IntegerField()
    bid_time_stamp = DateTimeField(primary_key=True)
    auction = ForeignKeyField(Auction)
