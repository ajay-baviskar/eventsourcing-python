from typing import List, cast, Set
from uuid import UUID, uuid5, NAMESPACE_URL
import requests
from eventsourcing.dispatch import singledispatchmethod
from eventsourcing.domain import Aggregate
from decimal import Decimal
import asyncio
import aiohttp
import json
from pathlib import Path
import os 
from dotenv import load_dotenv, dotenv_values

BASEDIR = os.path.abspath(os.path.dirname(__file__))

# Connect the path with your '.env' file name
load_dotenv(os.path.join(BASEDIR, 'variables.env'))

#@Author : Suhani
class GroupUserRegistry(Aggregate):  
    class Event(Aggregate.Event):
        def apply(self, aggregate: Aggregate) -> None:
            cast(GroupUserRegistry, aggregate).apply(self)

    class GroupUserFetched(Event, Aggregate.Created):
        data: List[str]
        

    class GroupUserAdded(Event):
        gid: str
        pid: str
        dist_id: str
        

    # Creates a UUID for GroupUserRegistry.
    @classmethod
    def create_id(cls) -> str:
        return uuid5(NAMESPACE_URL, f'/groupuserregistry/')

    @classmethod
    def fetch_all_groups(cls) -> List[str]:
        # Fetch all group IDs from the first API
        url = os.getenv('FETCH_GROUPS_URL')
        print("fetch_groups", url)
        response = requests.get(url)
        data = response.json().get('data', [])
        new_data = data['data']
        group_ids = []
        for i in new_data:
            group_ids.append(i['group_id'])
        return group_ids
    
    
    #dataa -> dict ({gid : {pid:distid, pid:distid}, gid : {pid:distid, pid:distid}})
    @classmethod
    async def fetch_group_users(cls, session, gid: str, dataa: dict) -> None:
        FETCH_USERS_URL = os.getenv('FETCH_USERS_URL')
        print("fetchusersurl", FETCH_USERS_URL)
        url = f"{FETCH_USERS_URL}/{gid}"
        async with session.get(url) as response:
            data = await response.json()
            for member in data.get('data', []):
                designation = member.get('designation')
                if designation == "MARKETERS":
                    user_id = member['user_id']
                    district_id = member['district_id']
                    existing_mapping = dataa.get(gid, {})  # Existing mapping for the group ID if it exists
                    # Check for duplicates and update the data only if it's not a duplicate
                    if user_id not in existing_mapping:
                        existing_mapping[user_id] = district_id
                    dataa[gid] = existing_mapping
            print("done", gid)


            
    @classmethod
    # Creates GroupUserRegistry.
    async def create(cls) -> "GroupUserRegistry":  # allowing non-blocking concurrent execution
        group_ids = cls.fetch_all_groups()
        dataa = {}
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(0, len(group_ids), 10):
                # Process group IDs in batches of 10
                batch_group_ids = group_ids[i:i + 10]
                for group_id in batch_group_ids:
                    task = asyncio.create_task(cls.fetch_group_users(session, group_id, dataa))
                    tasks.append(task)
                    await asyncio.sleep(0.1)  # Introduce a delay of half a second between requests
            await asyncio.gather(*tasks)  # Wait for all tasks to complete
        return cls._create(cls.GroupUserFetched, data= [dataa])
    
    def add_grp_user(self, gid, pid, dist_id) -> "GroupUserRegistry":
        self.trigger_event(self.GroupUserAdded, gid=gid, pid=pid, dist_id=dist_id)
        
    
    @singledispatchmethod
    def apply(self, event: Event) -> None:
        """Applies event to aggregate."""
    
    @apply.register
    def _(self, event: GroupUserFetched) -> None:
        self.data = event.data
        
    @apply.register
    def _(self, event: GroupUserAdded) -> None:
        self.gid = event.gid
        self.pid = event.pid
        self.dist_id = event.dist_id

###

class Player(Aggregate):
    class Event(Aggregate.Event):
        def apply(self, aggregate: Aggregate) -> None:
            cast(Player, aggregate).apply(self)

    class PlayerCreated(Event, Aggregate.Created):
        gid: str
        pid: str

    @classmethod
    def create_id(cls, gid: str, pid:str):
        return uuid5(NAMESPACE_URL, f'/player/{gid}/{pid}')
    
    @classmethod
    def create(cls, gid: str, pid:str) -> "Player":
        return cls._create(cls.PlayerCreated, gid=gid, pid=pid)

    @singledispatchmethod
    def apply(self, event: Event) -> None:
        """Applies event to aggregate."""

    @apply.register
    def _(self, event: PlayerCreated) -> None:
        self.gid = event.gid
        self.pid = event.pid
        
###


#PlayerRegistry: the registered players which are stored in the db after calling the register_player function.
class PlayerRegistry(Aggregate):
    class Event(Aggregate.Event):
        def apply(self, aggregate: Aggregate) -> None:
            cast(PlayerRegistry, aggregate).apply(self)

    class Registered(Event, Aggregate.Created):
        name: str

    class PlayerAdded(Event):
        player_id: UUID

    # Creates a UUID for PlayerRegistry.
    @classmethod
    def create_id(cls, name):
        return uuid5(NAMESPACE_URL, f'/registry/{name}')
    
    @classmethod
    def register(cls, name: str) -> "PlayerRegistry":
        return cls._create(cls.Registered, name=name)
    
    def register_player(self, player_id: UUID) -> None:
        if not player_id in self.player_ids:
            self.trigger_event(self.PlayerAdded, player_id=player_id)  
    
    @singledispatchmethod
    def apply(self, event: Event) -> None:
        """Applies event to aggregate."""

    @apply.register
    def _(self, event: Registered) -> None:
        self.name = event.name
        self.player_ids = set()

    @apply.register
    def _(self, event: PlayerAdded) -> None:
        self.player_ids.add(event.player_id)
        


###

# Creates monthly accounts for players. Takes gid,pid and mon-year as input for creating uuid.
# 1 account per player is created per month
class MonthlyAccount(Aggregate):  
    class Event(Aggregate.Event):
        def apply(self, aggregate: Aggregate) -> None:
            cast(MonthlyAccount, aggregate).apply(self)

    class MonthlyAccountCreated(Event, Aggregate.Created):
        gid: str
        pid: str
        mon_year: str
        balance: Decimal
        

    class CollectionAdded(Event):
        gid: str
        pid: str
        mon_year: str
        dt: str
        collection: Decimal
        tc: Decimal

    #@Author : Suhani        
    class CollectionUpdated(Event):
        gid: str
        pid: str
        mon_year: str
        dt: str
        collection: Decimal
        tc: Decimal

    @classmethod
    def create_id(cls, gid, pid, mon_year):
        return uuid5(NAMESPACE_URL, f'/MonthlyAccount/{gid}/{pid}/{mon_year}')    
        
    # Creates a new instance of MonthlyAccount.
    @classmethod
    def create(cls, gid, pid, mon_year) -> "MonthlyAccount":
        balance= Decimal('0.0')
        tc= Decimal('0.0')
        return cls._create(cls.MonthlyAccountCreated, gid=gid, pid=pid, mon_year=mon_year, balance= balance)


    def add_collection(self, gid, pid, mon_year, dt, tc, collection: Decimal) -> None:
        if not hasattr(self, 'dict3'):
            self.dict3 = {}
        if not hasattr(self, 'dict'):
            self.dict = {}
        self.dict[dt] = collection # Adds an entry to the dictionary self.dict with the key dt and value collection

        if dt not in self.dict3.keys():
            self.dict3[dt] = []  # Initialize list for each date if not present
        self.dict3[dt].append(collection)  
        self.balance += collection # Holds the cumilative monthly collection 
        if (self.tc != tc): # If tc is changed, tirgger the CollectionUpdated 
            self.tc=tc
            self.trigger_event(self.CollectionUpdated, gid=gid, pid=pid, mon_year=mon_year, dt=dt, collection=collection,tc=tc)
        # if tc is not changed, add collection as it is
        self.trigger_event(self.CollectionAdded, gid=gid, pid=pid, mon_year=mon_year, dt=dt, collection=collection,tc=tc)  

    #@Author : Suhani
    def update_collection(self, gid, pid,  mon_year, dt, new_collection, tc) -> None:
        if hasattr(self, 'dict') and dt in self.dict:
            # Update the collection in dictionary for the given date
            self.dict[dt] = new_collection
            #Update the tc if it is different
            # Trigger the CollectionUpdated event
            if (self.tc != tc): 
                self.tc=tc
            self.trigger_event(self.CollectionUpdated, gid=gid, pid=pid, mon_year=mon_year, dt=dt, collection=new_collection,tc=tc)

    
    #@Author : Suhani
    def get_collection_dict(self):
        return self.dict  
      
  
    @singledispatchmethod
    def apply(self, event: Event) -> None:
        """Applies event to aggregate."""


    @apply.register
    def _(self, event: MonthlyAccountCreated) -> None:
        self.gid = event.gid
        self.pid = event.pid
        self.mon_year = event.mon_year
        self.balance = Decimal('0.0')
        self.tc = Decimal('0.0')

          
    @apply.register    
    def _(self, event: CollectionAdded) -> None:
        self.gid = event.gid
        self.pid = event.pid
        self.mon_year = event.mon_year
        self.dt = event.dt
        self.balance += event.collection
        # Initialize self.dict if not present
        if not hasattr(self, 'dict'):
            self.dict = {}
        self.dict[self.dt] = event.collection
        self.tc = event.tc
        # Initialize self.dict3 if not present
        if not hasattr(self, 'dict3'):
            self.dict3 = {}
        # Append collection to existing list or initialize new list
        if self.dt in self.dict3:
            self.dict3[self.dt].append(event.collection)
        else:
            self.dict3[self.dt] = [event.collection]
            
            
    #@Author : Suhani
    # dict: {date : collection}
    # dict2: {date : tc}
    # dict3 : {date: [collections]}
    @apply.register
    def _(self, event: CollectionUpdated) -> None:
        self.gid = event.gid
        self.pid = event.pid
        self.mon_year = event.mon_year
        self.dt = event.dt
        if not hasattr(self, 'dict'):
            self.dict = {}
        self.dict[self.dt] = event.collection
        if not hasattr(self, 'dict2'):
            self.dict2 = {}
        self.dict2[self.dt] = event.tc
        if not hasattr(self, 'dict3'):
            self.dict3 = {}
