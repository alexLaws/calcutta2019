from setup import *
import datetime

database = SqliteDatabase('auction.db')


def accept_bids(team):
    bid_team = team
    bidder = input("What is your name?")

    print("The auction for {} starts now. Enter a number to bid.".format(bid_team))

    database.connect()
    database.execute_sql('PRAGMA foreign_keys = ON;')

    last_time = datetime.datetime.now()

    while True:
        try:
            amt = int(input("Bid: "))
        except:
            
        bid_time = datetime.datetime.now()

        time_gap = bid_time - last_time
        seconds = divmod(time_gap.total_seconds(), 60)[1]

        if seconds < 10:
            if Bids.select(fn.MAX(Bids.bid_amount)).scalar():
                curr_max = Bids.select(fn.MAX(Bids.bid_amount)).scalar()
            else:
                curr_max = 0

            if amt > curr_max:
                new_bid = Bids.create(participant=bidder,
                                      team_bid=bid_team,
                                      bid_amount=amt,
                                      bid_time_stamp=bid_time)
                new_bid.save()
                last_time = bid_time
            else:
                print("The bid is too low. Bid again.")
        else:
            print("The auction for {} is over. Your bid does not count".format(bid_team))
            break

if __name__ == "__main__":
    accept_bids("Duke")
