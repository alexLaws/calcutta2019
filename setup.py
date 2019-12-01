from model import Bid, Team, User, Auction, User_access, Auction_result, database
import datetime

database.drop_tables([Bid, Team, User, Auction, User_access, Auction_result])
database.create_tables([Bid, Team, User, Auction, User_access, Auction_result])

duke = Team(team="Duke Blue Devils")
duke.save()

georgetown = Team(team="Georgetown Hoyas")
georgetown.save()

gonzaga = Team(team="Gonzaga Bulldogs")
gonzaga.save()

alex = User(username='lawsalex',
            email='tal1286@gmail.com',
            first_name='Alex',
            last_name='Laws')
alex.set_password('admin')
alex.save()

chris = User(username='bubernakChris',
             email='Chris.Bubernak@gmail.com',
             first_name='Chris',
             last_name='Bubernak')
chris.set_password('captain')
chris.save()

keith = User(username='porcaroKeith',
             email='bluelightspecial@gmail.com',
             first_name='Keith',
             last_name='Porcaro')
keith.set_password('boston')
keith.save()

kober = Auction(auction_name="Kober6",
                code="crapfest",
                current_team=None)
kober.save()

seattle = Auction(auction_name="Voodoo",
                  code="do the doo",
                  current_team=None)
seattle.save()

boston = Auction(auction_name="WorstCoast",
                 code="Least",
                 current_team=None)
boston.save()

test = Auction(auction_name="test",
               code="test",
               current_team=None)
test.save()

User_access.create(user_in_auction=alex,
                   auction=kober)
User_access.create(user_in_auction=alex,
                   auction=seattle)
User_access.create(user_in_auction=alex,
                   auction=boston)
User_access.create(user_in_auction=alex,
                   auction=test)
User_access.create(user_in_auction=chris,
                   auction=seattle)
User_access.create(user_in_auction=keith,
                   auction=kober)
User_access.create(user_in_auction=keith,
                   auction=boston)
