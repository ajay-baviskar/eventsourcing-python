from eventsourcing.application import AggregateNotFound
from eventsourcing.system import ProcessApplication
from eventsourcing.dispatch import singledispatchmethod
from eventsourcing.domain import Aggregate, event
from model import MonthlyAccount
from uuid import uuid5, NAMESPACE_URL
from application import Gamification

# Initialize Gamification application
game = Gamification()

# Define the Counters class, which is a ProcessApplication
class Counters(ProcessApplication):
    @singledispatchmethod
    # Default policy method (called if no other policy matches)
    def policy(self, domain_event, process_event):
        """Default policy"""


    # Policy for handling CollectionAdded events
    # This is trigerred when the CollectionAdded function is called in the model.py
    @policy.register(MonthlyAccount.CollectionAdded)
    def _(self, domain_event, process_event):
        gid = domain_event.gid
        pid = domain_event.pid
        mon_year = domain_event.mon_year
        dt = domain_event.dt
        amount = domain_event.collection
        tc=domain_event.tc
        try:
            # Get Collection aggregate for the given month/year
            collection_id = Collection.create_id(gid, pid, mon_year)
            collection = self.repository.get(collection_id)
        except AggregateNotFound:
            # If Collection aggregate doesn't exist, create it
            collection = Collection(gid, pid, mon_year)

        try:
            # Get MonthlyAccount aggregate for the given month/year 
            monthly_account_id = MonthlyAccount.create_id(gid, pid, mon_year)
            monthly_account = game.repository.get(monthly_account_id)
        except AggregateNotFound:
            raise 
        
        # Calculate total monthly collection balance
        collection_dict = monthly_account.get_collection_dict()
        monthly_collection_balance = 0 
        for value in collection_dict.values():
            monthly_collection_balance += value

        
        #@Author : Suhani
        # Points calculation logic
        A = 160
        target = round(tc,2)
        if target == 0:
            x = 0
        else:
            x = round((float(amount)/target),10)
        actual_points = round(((A**x - 1) / (A - 1)) * (3000 * (target / 1000000)),9)

        # Determine bonus points based on the day of the month
        day = int(dt.split('-')[2])
        bonus_points = 0
        bpb1 = 0
        bpb2 = 0
        if day == 10:
            bpb1 = 2 * actual_points
        elif day == 20:
            bpb2 = actual_points
        if 1 <= day <= 10:
            bonus_points = 2 * actual_points
        elif 11 <= day <= 20:
            bonus_points =  actual_points + bpb1
        elif 21 <= day <= 31: 
            bonus_points = 0.1 * actual_points + bpb1 + bpb2 
        points = round(actual_points + bonus_points,10)
        
        #@Author : Suhani
        # Add points to the collection aggregate
        # Check if dt exists in collection.dates
        if dt not in collection.dates:
            # Call add_points with the correct parameter
            collection.add_points(dt, points,actual_points, bonus_points)
        else:
            print("Update")

        process_event.collect_events(collection)

    #@Author : Suhani
    @policy.register(MonthlyAccount.CollectionUpdated)
    def _(self, domain_event, process_event):
        gid = domain_event.gid
        pid = domain_event.pid
        mon_year = domain_event.mon_year
        dt = domain_event.dt
        tc = domain_event.tc
        # Access the MonthlyAccount aggregate
        try:
            monthly_account_id = MonthlyAccount.create_id(gid, pid, mon_year)
            monthly_account = game.repository.get(monthly_account_id)
        except AggregateNotFound:
            raise 

        # Calculate total monthly collection balance
        collection_dict = monthly_account.get_collection_dict()
        monthly_collection_balance = 0 
        for value in collection_dict.values():
            monthly_collection_balance += value

        try:
            # Get Collection aggregate for the given month/year
            collection_id = Collection.create_id(gid, pid, mon_year)
            collection = self.repository.get(collection_id)
        except AggregateNotFound:
            collection = Collection(gid, pid, mon_year)

        #@Author : Suhani
        A = 160
        target = tc
        
        points = 0
        x = 0
        actual_points = 0
        bpb1 = 0
        bpb2 = 0
        day10_points = 0
        day20_points = 0

        for i in collection_dict.keys():
            if target == 0:
                x = 0
            else:
                x += round((float(collection_dict[i]) / target), 10)
            actual_points = round((((A ** x) - 1) / (A - 1)) * (3000 * (target / 1000000)),9)
            # Determine bonus points based on the day of the month
            day = int(i.split('-')[2])

            bonus_points = 0
            if day == 10:
                bpb1 = 2 * actual_points
                day10_points = actual_points
            elif day == 20:
                bpb2 = actual_points - day10_points
                day20_points = actual_points
            if 1 <= day <= 10:
                bonus_points = 2 * actual_points
            elif 11 <= day <= 20:
                bonus_points =  actual_points - day10_points + bpb1
            elif 21 <= day <= 31: 
                bonus_points = (0.1 * (actual_points - day20_points)) + (bpb1 + bpb2) 

            points = actual_points + bonus_points
        # Update points in the collection aggregate
        collection.update_points(dt, points,actual_points, bonus_points)

        # Save the updated collection to the repository
        process_event.collect_events(collection)


    # Method to get total points for a given group, player, and month/year
    def get_collection_points(self, gid, pid, mon_year):
        collection_id = Collection.create_id(gid, pid, mon_year)
        try:
            collection = self.repository.get(collection_id)
        except AggregateNotFound:
            return 0
        return collection.points
    
    
    #@Author : Suhani
    # Method to get collection dates for a given group, player, and month/year
    def get_collection_dates(self, gid, pid, mon_year):
        collection_id = Collection.create_id(gid, pid, mon_year)
        try:
            collection = self.repository.get(collection_id)
        except AggregateNotFound:
            return []
        return collection.dates


# Define the Collection aggregate
class Collection(Aggregate):
    def __init__(self, gid, pid, mon_year):
        self.gid = gid
        self.pid = pid
        self.mon_year = mon_year
        self.points = 0
        self.actual_points = 0
        self.bonus_points = 0
        self.dates= []


    # Method to create ID for Collection aggregate
    @classmethod
    def create_id(cls, gid, pid, mon_year):
        return uuid5(NAMESPACE_URL, f'/collection/{gid}/{pid}/{mon_year}')

    # Event decorator to register PointsAdded events
    @event('PointsAdded')
    def add_points(self, dt, points, actual_points, bonus_points):
        self.dates.append(dt)
        self.points += points
        self.actual_points += actual_points
        self.bonus_points += bonus_points

    #@Author: Suhani
    # Event decorator to register PointsUpdated events
    @event('PointsUpdated')
    def update_points(self, dt, points, actual_points, bonus_points):
        self.dates.append(dt)
        self.points = points
        self.actual_points = actual_points
        self.bonus_points = bonus_points