#@Author : Suhani

from flask import Flask, request, jsonify, render_template, Response
from model import GroupUserRegistry
from application import Gamification
from points import Counters
import requests
from eventsourcing.system import SingleThreadedRunner
from eventsourcing.system import System
from datetime import datetime, timedelta
import aiohttp
import asyncio
import os
import logging
from dotenv import load_dotenv, dotenv_values

BASEDIR = os.path.abspath(os.path.dirname(__file__))

# Connect the path with your '.env' file name
load_dotenv(os.path.join(BASEDIR, 'variables.env'))

# Set up logging configuration
logging.basicConfig(filename='logs.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__)

# Initialize the event sourcing system
system = System(pipes=[[Gamification, Counters]])
runner = SingleThreadedRunner(system, env=None)
runner.start()

# Get the application objects.
game = runner.get(Gamification)
counters = runner.get(Counters)

# Route to fetch the group ids, user ids and district ids from the external apis and store them in DB.
# Register these players in the PlayerRegistry as well, simulataneously 
@app.route('/fetch', methods=['GET'])
def fetch():
    try:
        logging.info('Fetching data...')
        game.add_groups_and_users() # To fetch gid, pid, distid from API and save in DB
        logging.info('Data fetched successfully!')
        response = {
            "code": 200,
            "success": True,
            "message": "Data fetched successfully!"
        }
        return jsonify(response)
    except Exception as e:
        logging.error(f'Error fetching data: {str(e)}')
        response = {
            "code": 500,
            "success": False,
            "message": "Unsuccessful!"
        }
        return jsonify(response), 500


# Route to add the collection in db
# Takes mon-year as user input and gid pid from the PlayerRegistry in the db
@app.route('/add_collection', methods=['POST'])
def add_collection():
    try:
        data = request.get_json()
        mon_year = data.get('mon_year')
        logging.info(f'Request received to add collections for month-year: {mon_year}')
        
        # Fetch all groups and user IDs from PlayerRegistry
        all_ids = game.get_all_player_ids(name="players")
        for i in all_ids:
            gid, pid = game.get_pid_gid(i)
            logging.info(f'Processing GID: {gid}, PID: {pid}')
            records_for_month = get_records_for_month(int(gid), [int(pid)], mon_year)
            # Iterate over the records and add them to the database
            for record in records_for_month:
                dt = record['date']
                collection = record['achieved']
                tc = record['target']
                game.add_collection(gid, pid, dt, collection, tc)
        
        logging.info('Collections added successfully for all users!')
        response = {
            "code": 200,
            "success": True,
            "message": "Collections for users added successfully!"
        }
        return jsonify(response)
    except Exception as e:
        logging.error(f'Error adding collections: {str(e)}')
        response = {
            "code": 500,
            "success": False,
            "message": "Unsuccessful!"
        }
        return jsonify(response), 500

# Get the achieved collection and target collection for a whole month using external api 
# Takes the group id and player id from the GroupUserRegistry
def get_records_for_month(gid, pid, mon_year):
    try:
        api_url = os.getenv('API_URL')
        print("get_records_url",api_url)
        
        # Create a list to store records for the entire month
        all_records = []
        date_obj = datetime.strptime(mon_year, "%b-%y")
        month = date_obj.month
        year = date_obj.year
        # Get yesterday's date
        yesterday = datetime.now().date() - timedelta(days=1)

        # Iterate over the days of the month until yesterday's date
        days_in_month = range(1, min(yesterday.day, (datetime(year, month % 12 + 1, 1) - timedelta(days=1)).day) + 1)
        for day in days_in_month:
            dt = f"{year}-{month:02d}-{day:02d}"
            logging.info(f'Processing date: {dt}')
            
            # Make the API request for each day
            input_data = {
                "group_id": gid,
                "user_id": pid,
                "date": dt
            }
            response = requests.post(api_url, json=input_data)
            api_data = response.json()
            
            # Process the response and extract relevant information
            for record in api_data.get('data', []):
                for entry in record.get('records', []):
                    if entry.get('key') == 'collection_efficiency':
                        collection_record = entry
                        if collection_record['achieved'] is None:
                            collection_record['achieved'] = 0
                        if collection_record['target'] is None:
                            collection_record['target'] = 0

                        # Append relevant information to the list
                        all_records.append({
                            'date': dt,
                            'achieved': collection_record['achieved'],
                            'target': collection_record['target']
                        })
        return all_records
    except Exception as e:
        logging.error(f'Error getting records for month-year {mon_year}: {str(e)}')
        return []




@app.route('/rank', methods=['GET'])
def get_rank():
    try:
        dt = request.args.get('mon_year')
        rank_list = []

        # Fetch flag data from the provided API
        flag_api_url = f'http://194.163.171.206:30056/flag?mon_year={dt}'
        flag_response = requests.get(flag_api_url)
        flag_content = flag_response.text
        
        # Parse the table data assuming it's tab-separated
        flag_data_lines = flag_content.strip().split('\n')
        flag_dict = {}
        for line in flag_data_lines[1:]:
            cols = line.split('\t')
            gid = cols[0]
            pid = cols[1]
            flag_dict[(gid, pid)] = 'F'
        # Iterate over the PlayerRegistry for gid and pid 
        all_ids = game.get_all_player_ids(name="players")
        for i in all_ids:
            gid, pid = game.get_pid_gid(i)
            points = counters.get_collection_points(gid=gid, pid=pid, mon_year=dt)

            # Check if there is a flag for this GID and PID
            flag = flag_dict.get((gid, pid), '')

            rank_dict = {
                'GID': gid,
                'PID': pid,
                'Points': round(points, 2),
                'Flag': flag
            }
            rank_list.append(rank_dict)

        # Sort the list of dictionaries by the 'Points' key in descending order
        sorted_rank = sorted(rank_list, key=lambda x: x['Points'], reverse=True)

        for idx, player_info in enumerate(sorted_rank, start=1):
            player_info['Rank'] = idx

        return render_template('rank.html', rank_list=sorted_rank, mon_year=dt)
    except Exception as e:
        logging.error(f'Error in get_rank function: {str(e)}')
        # Handle the error gracefully, e.g., return an error page or message
        return str(e)


# Takes mon-year as user input.
# Ranks all the players according to points by accessing their payer ids then their collection points
# @app.route('/rank', methods=['GET'])
# def get_rank():
#     try:
#         dt = request.args.get('mon_year')
#         rank_list = []

#         # Iterate over the PlayerRegistry for gid and pid 
#         all_ids = game.get_all_player_ids(name="players")
#         for i in all_ids:
#             gid, pid = game.get_pid_gid(i)
#             points = counters.get_collection_points(gid=gid, pid=pid, mon_year=dt)

#             rank_dict = {
#                 'GID': gid,
#                 'PID': pid,
#                 'Points': round(points,2)
#             }
#             rank_list.append(rank_dict)

#         # Sort the list of dictionaries by the 'Points' key in descending order
#         sorted_rank = sorted(rank_list, key=lambda x: x['Points'], reverse=True)

#         for idx, player_info in enumerate(sorted_rank, start=1):
#             player_info['Rank'] = idx

#         return render_template('rank.html', rank_list=sorted_rank, mon_year=dt)
#     except Exception as e:
#         logging.error(f'Error in get_rank function: {str(e)}')
#         # Handle the error gracefully, e.g., return an error page or message
#         return render_template('error.html', error_message=str(e))


# Takes mon-year and district id as user input
# Access the GroupUserRegistry. check for matching district id and gets their points and ranks those players
@app.route('/district_rank', methods=['GET', 'POST'])
def get_district_rank():
    try:
        if request.method == 'POST':
            dt = request.form.get('mon_year')
            district_id = request.form.get('district_id')

            rank_list = []
            group_user_registry = game.repository.get(GroupUserRegistry.create_id())
            group_data = group_user_registry.data[0]

            for gid, player_dict in group_data.items():
                for pid, player_district_id in player_dict.items():
                    if district_id == player_district_id:
                        points = counters.get_collection_points(gid=gid, pid=pid, mon_year=dt)
                        rank_dict = {
                            'GID': gid,
                            'PID': pid,
                            'District': player_district_id,
                            'Points': points
                        }
                        rank_list.append(rank_dict)

            sorted_rank = sorted(rank_list, key=lambda x: x['Points'], reverse=True)

            for idx, player_info in enumerate(sorted_rank, start=1):
                player_info['Rank'] = idx

            return render_template('district_rank.html', rank_list=sorted_rank, mon_year=dt, district_id=district_id)
        else:
            return render_template('district_rank.html', rank_list=[])
    except Exception as e:
        logging.error(f'Error in get_district_rank function: {str(e)}')
        # Handle the error gracefully, e.g., return an error page or message
        return render_template('error.html', error_message=str(e))


# To generate monthly report of a user.
# Takes gid, pid, mon-year as user input
# Generates 3 tables
# Table 1: the monthly achieved collection, target collection
# Table 2: monthly updated target collection
# Table 3: monthly updated achieved collection
@app.route("/user_report", methods=['GET'])
def get_user_report():
    try:
        mon_year = request.args.get('mon_year')
        gid = request.args.get('gid')
        pid = request.args.get('pid')
        table_data = []
        table_data2 = []

        # Check if gid and pid are not None before converting to integers
        if gid is not None and pid is not None:
            gid = int(gid)
            pid = int(pid)

            # TC Report
            results = game.get_data(gid, pid, mon_year)
            if results != 0:
                prev_j = 0
                if hasattr(results, 'dict2'):
                    for date, j in results.dict2.items():
                        if prev_j is not None and round(prev_j,2) != round(j,2):
                            if j != 0 and prev_j != 0:
                                entry = {
                                    'gid': gid,
                                    'pid': pid,
                                    'date': date,
                                    'prev_tc': round(prev_j,2),
                                    'updated_tc': round(j,2)
                                }
                                table_data.append(entry)
                            prev_j = j

                # Collection Report
                if hasattr(results, 'dict3'):
                    dates = list(results.dict3.keys())

                    for date in sorted(set(dates)):  # Sort dates in ascending order
                        collection_list = results.dict3[date]

                        # Check if collection_list is a list
                        if isinstance(collection_list, list):
                            for i in range(len(collection_list) - 1):
                                prev_collection = collection_list[i]
                                updated_collection = collection_list[i + 1]

                                entry = {
                                    'gid': gid,
                                    'pid': pid,
                                    'date': date,
                                    'prev_collection': prev_collection,
                                    'updated_collection': updated_collection
                                }
                                table_data2.append(entry)

            records_for_month = get_records_for_month(gid, [pid], mon_year)

            return render_template('user_report.html', table_data=table_data, table_data2=table_data2, records_for_month=records_for_month, mon_year=mon_year, gid=gid, pid=pid)
        else:
            # Handle the case where gid or pid is None
            return render_template('user_report.html', error_message="GID and PID must be provided.")
    except Exception as e:
        logging.error(f'Error in get_user_report function: {str(e)}')
        # Handle the error gracefully, e.g., return an error page or message
        return render_template('error.html', error_message=str(e))



# @app.route('/flag', methods=['GET'])
# def get_flag():
#     flag = 0
#     mon_year = request.args.get('mon_year')
#     all_ids = game.get_all_player_ids(name="players")
#     table_data = []
#     for i in all_ids:
#         gid, pid = game.get_pid_gid(i)
#         results = game.get_data(gid, pid, mon_year)
#         balance = sum(results.dict.values())
#         if results != 0:
#             var = results.dict2[list(results.dict2)[-1]]
#             if var <= balance:
#                 flag+=1
#                 print("FLAG",flag)
#         return ("OK")


# from collections import defaultdict

# @app.route('/flag2', methods=['GET'])
# def get_flag2():
#     try:
#         mon_year = request.args.get('mon_year')
#         all_ids = game.get_all_player_ids(name="players")
#         table_data = []

#         # Get data for all players at once
#         player_data = defaultdict(dict)
#         for i in all_ids:
#             gid, pid = game.get_pid_gid(i)
#             print(gid,pid)
#             results = game.get_data(gid, pid, mon_year)
#             if results != 0:
#                 player_data[(gid, pid)] = results
#                 print(player_data[(gid, pid)])
#         # Process player data
#         for (gid, pid), results in player_data.items():
#             balance = sum(results.dict.values())
#             var = results.dict2[list(results.dict2)[-1]]
#             if var <= balance:
#                 if balance != 0 or var != 0:
#                     table_data.append({'gid': gid, 'pid': pid})

#         return render_template('flag.html', table_data=table_data, mon_year=mon_year)
#     except Exception as e:
#         logging.error(f'Error in get_flag function: {str(e)}')
#         return render_template('error.html', error_message=str(e))


@app.route('/flag', methods=['GET'])
def get_flag():
    try:
        flag = 0
        mon_year = request.args.get('mon_year')
        all_ids = game.get_all_player_ids(name="players")
        table_data = []
        for i in all_ids:
            gid, pid = game.get_pid_gid(i)
            print(gid,pid)
            results = game.get_data(gid, pid, mon_year)
            print(results)
            if results != 0:
                balance = sum(results.dict.values())
                var = results.dict2[list(results.dict2)[-1]]
                print("TC",var)
                if var <= balance:
                    flag+=1
                    if balance !=0 or var !=0:
                        entry = {
                            'gid': gid,
                            'pid': pid,
                        }
                        table_data.append(entry)
        return render_template('flag.html', table_data=table_data, mon_year=mon_year)
    except Exception as e:
        logging.error(f'Error in get_flag function: {str(e)}')
        # Handle the error gracefully, e.g., return an error page or message
        return render_template('error.html', error_message=str(e))


# Generates the updated target colletion of all users.
# Takes mon-year as user input
@app.route("/tc_report", methods=['GET'])
def get_report():
    try:
        mon_year = request.args.get('mon_year')

        all_ids = game.get_all_player_ids(name="players")
        table_data = []

        for i in all_ids:
            gid, pid = game.get_pid_gid(i)
            results = game.get_data(gid, pid, mon_year)
            if results != 0:
                prev_j = 0
                if hasattr(results, 'dict2'):
                    for date, j in results.dict2.items():
                        if prev_j is not None and round(prev_j,2) != round(j,2):
                            if j != 0 and prev_j != 0:
                                entry = {
                                    'gid': gid,
                                    'pid': pid,
                                    'date': date,
                                    'prev_tc': round(prev_j,2),
                                    'updated_tc': round(j,2)
                                }
                                table_data.append(entry)
                            prev_j = j

        return render_template('tc_report.html', table_data=table_data, mon_year=mon_year)
    except Exception as e:
        logging.error(f'Error in get_report function: {str(e)}')
        # Handle the error gracefully, e.g., return an error page or message
        return render_template('error.html', error_message=str(e))

# Generate the updated achieved collection of all users
# Takes mon-year as input
@app.route("/collection_report", methods=['GET', 'POST'])
def get_collection_report():
    try:
        if request.method == 'POST':
            mon_year = request.form.get('mon_year')
        else:
            mon_year = request.args.get('mon_year')

        all_ids = game.get_all_player_ids(name="players")
        table_data = []

        for i in all_ids:
            gid, pid = game.get_pid_gid(i)

            results = game.get_data(gid, pid, mon_year)
            if results != 0:
                if hasattr(results, 'dict3'):
                    dates = list(results.dict3.keys())

                    for date in sorted(set(dates)):  # Sort dates in ascending order
                        collection_list = results.dict3[date]

                        # Check if collection_list is a list
                        if isinstance(collection_list, list):
                            for i in range(len(collection_list) - 1):
                                prev_collection = collection_list[i]
                                updated_collection = collection_list[i + 1]

                                entry = {
                                    'gid': gid,
                                    'pid': pid,
                                    'date': date,
                                    'prev_collection': prev_collection,
                                    'updated_collection': updated_collection
                                }
                                table_data.append(entry)

        # Sort table_data based on 'date' key in ascending order
        table_data.sort(key=lambda x: x['date'])

        return render_template('collection_report.html', table_data=table_data, mon_year=mon_year)
    except Exception as e:
        logging.error(f'Error in get_collection_report function: {str(e)}')
        # Handle the error gracefully, e.g., return an error page or message
        return render_template('error.html', error_message=str(e))

if __name__ == '__main__':
    host=os.getenv('FLASK_RUN_HOST')
    port=os.getenv('FLASK_RUN_PORT')
    app.run(host,port,debug=True)
    print("HOST",host)
    print("PORT",port)
    runner.stop()