import os
import datetime

from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from pusher import Pusher
import uuid

from model import Bid, Team, User, Auction, User_access, Auction_result
import model

from peewee import fn

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo

from flask_login import LoginManager, current_user, login_user, logout_user, login_required

from werkzeug.urls import url_parse
from werkzeug.exceptions import abort

import random

from time import sleep

# create flask app
app = Flask(__name__)
# app.secret_key = os.environ.get('SECRET_KEY').encode()

SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

sign_in = LoginManager(app)
sign_in.login_view = 'login'

# create Pusher app
pusher = Pusher(
    app_id='732112',
    key="162355e8decc1f5cd0a7",
    secret="bafc69ad0a7e680e2139",
    cluster="us2",
    ssl=True)

time_left = 20


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user_count = User.select(fn.Count(User.username)).where(User.username == username.data).scalar()
        if user_count == 1:
            raise ValidationError('There is already a user with that username.')

    def validate_email(self, email):
        user_count = User.select(fn.Count(User.email)).where(User.email == email.data).scalar()
        if user_count == 1:
            raise ValidationError('There is already a user with that email.')


class NewAuctionForm(FlaskForm):
    auction_name = StringField('Auction Name', validators=[DataRequired()])
    code = PasswordField('Auction Code', validators=[DataRequired()])
    code2 = PasswordField('Repeat Auction Code', validators=[DataRequired(), EqualTo('code')])
    submit = SubmitField('Create Auction')

    def validate_auction_name(self, auction_name):
        auction_count = Auction.select(fn.Count(Auction.auction_name)).where(Auction.auction_name == auction_name.data).scalar()
        if auction_count == 1:
            raise ValidationError('There is already an auction with that name.')


class JoinAuctionForm(FlaskForm):
    auction_name = StringField('Auction Name', validators=[DataRequired()])
    code = PasswordField('Auction Code', validators=[DataRequired()])
    submit = SubmitField('Join!')


def get_object_or_404(model, *criterion):
    output = model.select().where(*criterion).get()
    if output is None:
        abort(404)
    else:
        return output


def get_auction_obj(auction_name):
    try:
        curr = Auction.select().where(Auction.auction_name == auction_name).get()
        return curr
    except Auction.DoesNotExist:
        return False


def get_current_team(auction_name):
    try:
        curr = Auction.select(Auction.current_team).where(Auction.auction_name == auction_name).get()
        return curr.current_team
    except Auction.DoesNotExist:
        return False


def user_from_username(username):
    try:
        user = User.select().where(User.username == username).get()
        return user
    except User.DoesNotExist:
        return False


def get_leader(auction):
    team_for_bid = get_current_team(auction.auction_name)
    if team_for_bid:
        try:
            high_bid = Bid.select(fn.MAX(Bid.bid_amount)).where((Bid.team_bid == team_for_bid) &
                                                                (Bid.auction == auction)).scalar()
            leader = Bid.select().where((Bid.team_bid == team_for_bid) &
                                        (Bid.bid_amount == high_bid) &
                                        (Bid.auction == auction)).get()
            bid_leader = leader.participant
        except Bid.DoesNotExist:
            high_bid = 0
            bid_leader = 'Nobody'
        return team_for_bid, high_bid, bid_leader
    else:
        return False


def get_next_team(auction):
    taken_teams = []
    try:
        taken = Auction_result.select(Auction_result.team).where(Auction_result.auction == auction)
        for result in taken:
            taken_teams.append(result.team)
    except Auction_result.DoesNotExist:
        pass
    print(taken_teams)
    try:
        available_teams = Team.select().where(Team.team.not_in(taken_teams))
    except Team.DoesNotExist:
        return False
    print(available_teams)
    for team in available_teams:
        print(team)
    return random.choice(available_teams)


@app.route('/')
def home():
    return render_template('home.jinja2')


@sign_in.user_loader
def load_user(id):
    return User.select().where(User.id == id).get()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.select().where(User.username == form.username.data).get()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('home')
        return redirect(next_page)
    return render_template('login.jinja2', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data,
                    email=form.email.data,
                    first_name=form.first.data,
                    last_name=form.last.data)
        user.set_password(form.password.data)
        user.save()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.jinja2', title='Register', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/start/<auction_name>', methods=['POST'])
@login_required
def start_auction(auction_name):
    global time_left
    auction = get_auction_obj(auction_name)
    available_teams = list(Team.select())
    while True:
        try:
            team_up_for_bids = random.choice(available_teams)
        except IndexError:
            Auction.update({Auction.current_team: None}).where(Auction.auction_name == auction_name).execute()
            Auction.update({Auction.complete: True}).where(Auction.auction_name == auction_name).execute()
            data = {'id': "bid-{}".format(uuid.uuid4().hex),
                    'team': 'sale',
                    'bidder': 'The Auction is Over!',
                    'bid_amt': '',
                    'status': 'active',
                    'event_name': 'created',
                    'reset': 1
                    }
            pusher.trigger(auction_name, "bid-added", data)
            break
        available_teams.remove(team_up_for_bids)
        Auction.update({Auction.current_team: team_up_for_bids}).where(Auction.auction_name == auction_name).execute()
        data = {'id': "bid-{}".format(uuid.uuid4().hex),
                'team': 'sale',
                'bidder': 'Bidding Begins',
                'bid_amt': team_up_for_bids.team,
                'status': 'active',
                'event_name': 'created',
                'reset': 1
                }
        pusher.trigger(auction_name, "bid-added", data)
        time_left = 20
        while time_left > 0:
            data = {'id': "bid-{}".format(uuid.uuid4().hex),
                    'time_remaining': time_left,
                    'status': 'active',
                    'event_name': 'created',
                    'reset': 1
                    }
            pusher.trigger(auction_name, "timing", data)
            time_left = time_left - 1
            sleep(1)
        data = {'id': "bid-{}".format(uuid.uuid4().hex),
                'time_remaining': time_left,
                'status': 'active',
                'event_name': 'created',
                'reset': 1
                }
        pusher.trigger(auction_name, "timing", data)
        data = {'id': "bid-{}".format(uuid.uuid4().hex),
                'team': 'sale',
                'bidder': 'Team sold!',
                'bid_amt': '',
                'status': 'active',
                'event_name': 'created',
                'reset': 1
                }
        pusher.trigger(auction_name, "bid-added", data)
        team_for_bid, high_bid, bid_leader = get_leader(auction)
        Auction_result.create(auction=auction,
                              team=team_up_for_bids,
                              buyer=bid_leader,
                              price=high_bid)
        sleep(3)
    return 'hooray'


# store new bid
@app.route('/bid', methods=['POST'])
@login_required
def addBid():
    global time_left
    bidder = user_from_username(request.form['name'])
    bid_amt = int(request.form['bid'])
    auction_name = request.form['auction']
    auction = Auction.select().where(Auction.auction_name == auction_name).get()
    team_for_bid, high_bid, bid_leader = get_leader(auction)
    if bid_amt > high_bid and time_left > 0:
        Bid.create(participant=bidder,
                   team_bid=team_for_bid,
                   bid_amount=bid_amt,
                   bid_time_stamp=datetime.datetime.now(),
                   auction=auction)
        data = {'id': "bid-{}".format(uuid.uuid4().hex),
                'team': team_for_bid.team,
                'bidder': bidder.username,
                'bid_amt': bid_amt,
                'status': 'active',
                'event_name': 'created',
                'reset': 1
                }
        pusher.trigger(auction_name, "bid-added", data)
        time_left = 10
        return jsonify(data)
    else:
        message = bidder.username + ' - FAILED BID'
        data = {'id': "bid-{}".format(uuid.uuid4().hex),
                'team': team_for_bid.team,
                'bidder': message,
                'bid_amt': bid_amt,
                'status': 'active',
                'event_name': 'created',
                'reset': 0
                }
        pusher.trigger(auction_name, "bid-added", data)
        return jsonify(data)


@app.route('/view/')
@login_required
def view():
    all_teams = Team.select()
    all_bids = Bid.select().where(Bid.team_bid == all_teams[0]).order_by(Bid.bid_amount)
    return render_template('view.jinja2', all_teams=all_teams, bids=all_bids)


@app.route('/user/<username>')
@login_required
def user(username):
    user = get_object_or_404(User, User.username == username)
    auctions = User_access.select().where(User_access.user_in_auction == user)
    return render_template('user.jinja2', user=user, auctions=auctions)


@app.route('/auction/<auction_name>', methods=['GET', 'POST'])
@login_required
def auction(auction_name):
    auction = Auction.select().where(Auction.auction_name == auction_name).get()
    finished = auction.complete
    try:
        team_for_bid, high_bid, bid_leader = get_leader(auction)
    except TypeError:
        return render_template('auction.jinja2',
                               team=False,
                               leader=False,
                               high_bid=0,
                               auction=auction,
                               finished=finished)
    return render_template('auction.jinja2',
                           team=team_for_bid.team,
                           leader=bid_leader,
                           high_bid=high_bid,
                           auction=auction,
                           finished=finished)


@app.route('/newAuction', methods=['GET', 'POST'])
@login_required
def new_auction():
    form = NewAuctionForm()
    if form.validate_on_submit():
        created_auction = Auction(auction_name=form.auction_name.data,
                                  code=form.code.data)
        created_auction.save()
        user = User.select().where(User.username == current_user.username).get()
        new_access = User_access(user_in_auction=user,
                                 auction=created_auction)
        new_access.save()
        flash('Congratulations, you have created a new auction!')
        return redirect(url_for('user', username=current_user.username))
    return render_template('newAuction.jinja2', form=form)


@app.route('/joinAuction', methods=['GET', 'POST'])
@login_required
def join():
    form = JoinAuctionForm()
    if form.validate_on_submit():
        join_auction = Auction.select().where(Auction.auction_name == form.auction_name.data).get()
        if join_auction is None:
            flash('Auction Does Not Exist')
            return redirect(url_for('join'))
        elif form.code.data == join_auction.code:
            user = User.select().where(User.username == current_user.username).get()
            new_access = User_access(user_in_auction=user,
                                     auction=join_auction)
            new_access.save()
        return redirect(url_for('user', username=current_user.username))
    return render_template('join.jinja2', form=form)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6738))
    app.run(host='0.0.0.0', port=port)
