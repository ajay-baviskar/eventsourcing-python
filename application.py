from __future__ import annotations
from typing import Any, Dict
from uuid import UUID, NAMESPACE_URL
from datetime import datetime
from decimal import Decimal
import json
from eventsourcing.application import Application
from eventsourcing.application import Application, AggregateNotFound
from model import Player, PlayerRegistry, MonthlyAccount, GroupUserRegistry
import os
import asyncio
from typing import List, cast, Set
import requests
import aiohttp
from dotenv import load_dotenv, dotenv_values

BASEDIR = os.path.abspath(os.path.dirname(__file__))

# Connect the path with your '.env' file name
load_dotenv(os.path.join(BASEDIR, 'variables.env'))

#LOCAL DB
persistence_module = os.getenv('PERSISTENCE_MODULE')
postgres_dbname = os.getenv("POSTGRES_DBNAME")
postgres_host = os.getenv('POSTGRES_HOST')
postgres_port = os.getenv('POSTGRES_PORT')
postgres_user = os.getenv('POSTGRES_USER')
postgres_password = os.getenv('POSTGRES_PASSWORD')

print(persistence_module)
print(postgres_dbname)
print(postgres_host)
print(postgres_port)
print(postgres_user)
print(postgres_password)
    


#LOCAL SQLITE DB
# os.environ["PERSISTENCE_MODULE"] = 'eventsourcing.sqlite'
# os.environ["SQLITE_DBNAME"] = 'player66.db'

# Custom JSON Encoder for handling Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


# Application initialization
class Gamification(Application):
    is_snapshotting_enabled = True

    # Method to create player uuid 
    def create_player(self, gid: str, pid: str) -> UUID:
        player =self.get_player(gid,pid)
        return player.id
    
    # Method to fetch the player id from repo(database)
    def get_player(self, gid, pid):
        player_id= Player.create_id(gid, pid) # Player aggregate in model.py
        try:
            player = self.repository.get(player_id) 
        except AggregateNotFound:
            player = Player.create(gid, pid) # Creating new player objects
            self.save(player)
        return player

    
    # Method to check if a player exists in the playerregistry
    def check_if_player_exist(self, gid, pid):
        player_id= Player.create_id(gid, pid)
        try:
            player = self.repository.get(player_id)
            return player
        except AggregateNotFound:
            return 0

    
    # Method to register a player in PlayerRegistry
    def register_player(self, player_id: UUID) -> None:
        registry = self.get_players_registry(name='players') # name='players' for creating UUID
        registry.register_player(player_id=player_id) # triggers the PlayerAdded event in model.py
        self.save(registry) # saves the player in PlayerRegistry
        
    # to fetch the player registry. Player registry: when a player is registered using the register_player function, he is stored in the player registry
    def get_players_registry(self, name):
        registry_id= PlayerRegistry.create_id(name)
        try:
            registry = self.repository.get(registry_id) # Fetch the PlayerRegistry aggregate using id
        except AggregateNotFound:
            registry = PlayerRegistry.register(name) #  Create PlayerRegistry
            self.save(registry)
        return registry

    def register_player2(self,gid,pid):    
        player_id = self.create_player(gid, pid)
        self.register_player(player_id)

    def add_groups_and_users(self) -> None:
        # Create an instance of GroupUserRegistry and fetch data from APIs
        group_user_registry = asyncio.run(GroupUserRegistry.create())
        print(group_user_registry)
        group_user_registry_data = group_user_registry.data
        group_user_registry1 = group_user_registry_data[0]
        for gid in group_user_registry1.keys():
            for pid,dist_id in group_user_registry1[gid].items():
                group_user_registry.add_grp_user(gid=gid, pid=pid, dist_id=dist_id)  
                self.register_player2(gid, pid)
        registry_id= GroupUserRegistry.create_id()
        try:
            group_user_registry = self.repository.get(registry_id)
        except AggregateNotFound:
            self.save(group_user_registry)
        
    # Method to add the achieved collection in the db. Takes month-year as input.
    def add_collection(self, gid, pid, dt, collection: Decimal,tc) -> None:
        mon_year=datetime.strptime(dt, '%Y-%m-%d').strftime('%b-%y').upper() 
        self.check_if_player_exist(gid,pid) # Check if player is registered
        if self.check_if_player_exist(gid,pid) != 0:
            monthly_collection= self.get_monthly_collection(gid=gid, pid=pid, mon_year=mon_year)
            monthly_collection.add_collection(gid=gid, pid=pid, mon_year=mon_year, dt=dt, collection=collection,tc=tc) # in model.py
            self.save(monthly_collection) # Save in the DB
            return 1 # Success
        else:
            return 0 # Player not registered
    
    # Method to access the monthly collection singular event from the db
    def get_monthly_collection(self, gid, pid, mon_year):               
        monthly_collection_id= MonthlyAccount.create_id(gid=gid, pid=pid, mon_year=mon_year)  # Check if aggregate exists
        try:
            monthly_collection = self.repository.get(monthly_collection_id)
        except AggregateNotFound:
            monthly_collection = MonthlyAccount.create(gid=gid, pid=pid, mon_year=mon_year) # Create new monthly account aggregate
            self.save(monthly_collection) # Save in DB
        return monthly_collection
    
    
    # @Author : Suhani
    # Method to update the achieved collection/target collection if there is a change         
    def update_collection(self, gid, pid, dt, new_collection: Decimal, tc) -> int:
        mon_year = datetime.strptime(dt, '%Y-%m-%d').strftime('%b-%y').upper()
        monthly_collection = self.get_monthly_collection(gid=gid, pid=pid, mon_year=mon_year)
        # Get the old collection value for the given date from monthly collection dictionary
        old_collection = monthly_collection.dict[dt]
        # Update the collection for the given date
        monthly_collection.dict[dt] = new_collection
        # Recalculate the balance using all updated collection values
        monthly_collection_balance = sum(monthly_collection.dict.values())
        monthly_collection.balance = monthly_collection_balance
        monthly_collection.update_collection(gid=gid, pid=pid, mon_year=mon_year, dt=dt, new_collection=new_collection, tc=tc)
        # Save in DB
        self.save(monthly_collection)
        return 1, old_collection  # Success


    # Method to fetch the monthly data from the db. Called in app.py
    def get_data(self,gid,pid,mon_year):
        monthly_collection_id= MonthlyAccount.create_id(gid=gid, pid=pid, mon_year=mon_year)
        try:
            monthly_collection = self.repository.get(monthly_collection_id)
        except AggregateNotFound:
            monthly_collection = 0
        return monthly_collection
    
    #@Author : Suhani
    # Method to extract all player ids from the db using player registry
    def get_all_player_ids(self,name):
        registry_id= PlayerRegistry.create_id(name)
        try:
            registry = self.repository.get(registry_id)
        except AggregateNotFound:
            registry = PlayerRegistry.register(name)
            self.save(registry)
        return registry.player_ids
    
    #@Auhthor : Suhani
    #Method to fetch the group id and player id of a player
    def get_pid_gid(self,uuid):
        user_data = self.repository.get(uuid)
        extracted_gid = user_data.gid
        extracted_pid = user_data.pid
        return extracted_gid, extracted_pid  

# os.environ['PERSISTENCE_MODULE'] = 'eventsourcing.postgres'
# os.environ['POSTGRES_DBNAME'] = 'two_player'
# os.environ['POSTGRES_HOST'] = 'localhost'
# os.environ['POSTGRES_PORT'] = '5432'
# os.environ['POSTGRES_USER'] = 'postgres'
# os.environ['POSTGRES_PASSWORD'] = 'root'
