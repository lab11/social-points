from flask import Flask, render_template, request, g, make_response, redirect
import json
import sqlite3
import time
import pagerank
import numpy as np
import math

days = ['m', 't', 'w', 'th', 'f', 's', 'su']

app = Flask(__name__)
#XXX: Remove this at some point
app.debug = True
#app.config.from_object('fl_config')

def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = g.db = sqlite3.connect('../db/opo_data.db')
    return db

@app.before_request
def before_request():
    g.site_root = ''
    if 'X-Script-Name' in request.headers:
            g.site_root = request.headers['X-Script-Name']

    g.host = 'localhost'
    if 'Host' in request.headers:
            g.host = request.headers['Host']

    g.meta = {'root': g.site_root}


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/')
def home():
    return render_template('home.html', meta=g.meta)

@app.route('/linear')
def linear_leaderboard():
    return render_template('leaderboard.html', meta=g.meta, algo_type='linear')

@app.route('/pagerank')
def pagerank_leaderboard():
    return render_template('leaderboard.html', meta=g.meta, algo_type='pagerank')

@app.route('/<uniqname>')
def show_user_data(uniqname):
    #XXX: It would be cool to make this so that it displays user data
    #   individually in some useful way
    return "Your uniqname is " + str(uniqname)

def get_db_interactions(cur, id, start_time, end_time):
    results = []
    executed = False
    while not executed:
        try:
            request_tuple = (id, start_time, end_time)
            cur.execute("SELECT Last_Heard_ID FROM Interactions " + \
                "WHERE Id = ? AND Time >= ? AND Time < ? ORDER BY Time",
                request_tuple)
            results = cur.fetchall()
            executed = True
        except sqlite3.OperationalError:
            # just try again
            pass

    interactions = {}
    for record in results:
        last_heard_id = record[0]
        if last_heard_id not in interactions:
            interactions[last_heard_id] = 0
        else:
            interactions[last_heard_id] += 1

    return interactions

def get_db_identifications(cur):
    results = []
    executed = False
    while not executed:
        try:
            cur.execute("SELECT * FROM Identifications")
            results = cur.fetchall()
            executed = True
        except sqlite3.OperationalError:
            # just try again
            pass

    return results

@app.route('/group_info')
def group_info():
    
    algo_type = request.args.get('algo_type')
    cur = get_db().cursor()

    sec_since_start_of_day = time.localtime().tm_sec + \
            time.localtime().tm_min*60 + time.localtime().tm_hour*3600
    start_of_day_epoch = time.time() - sec_since_start_of_day
    week_ago_epoch = start_of_day_epoch - 7*24*3600

    ids = get_db_identifications(cur)

    interact_dict = {}
    for (full_name, uniqname, id) in ids:
        interact_dict[id] = {}
        start_time = week_ago_epoch
        while start_time < time.time():
            end_time = start_time + 24*3600
            interactions = get_db_interactions(cur, id, start_time, end_time)
            interact_dict[id][time.localtime(start_time).tm_wday] = interactions
            start_time = end_time

    data = []

    print(str(ids))

    # pagerank points allocation
    if algo_type == 'pagerank':

        # calculate pagerank on a day-by-day basis
        results = {}
        for day in range(7):
            # create pagerank graph
            pr_graph = []
            for (_, _, my_id) in ids:

                # find interactions with all other ids
                pr_row = []
                for (_, _, their_id) in ids:
                    # sum interactions with this id
                    interactions = 0
                    if their_id in interact_dict[my_id][day]:
                        interactions += interact_dict[my_id][day][their_id]

                    # insert into row
                    pr_row.append(interactions)

                # insert into pagerank graph
                pr_graph.append(pr_row)

            # run pagerank algorithm
            if 0:
                pr_graph = np.array([[0,0,1,0,0,0,0,0],
                                     [0,1,1,0,0,0,0,0],
                                     [1,0,1,1,0,0,0,0],
                                     [0,0,0,1,1,0,0,0],
                                     [0,0,0,0,0,0,1,0],
                                     [0,0,0,0,0,1,1,0],
                                     [0,0,0,1,1,0,1,0],
                                     [0,0,0,0,0,0,0,0]])
 
            print("\nAt time: " + str(time.time()))
            print(str(pr_graph))
            results[day] = pagerank.pageRank(np.array(pr_graph), maxerr = 0.1)
            print(str(results[day]))
            for value in results[day]:
                if math.isnan(value):
                    results[day] = [1/float(len(ids))]*len(ids)
                    break

        # create data for graphing
        id_index = 0
        for (full_name, uniqname, id) in ids:
            total_points = 0
            point_dict = {}
            point_dict['full_name'] = full_name
            point_dict['uniqname'] = uniqname
            point_counts = []
            for day_num in range(7):
                day_points = {}
                day_points['day'] = days[day_num]
                day_points['points'] = round(results[day_num][id_index]*100000)
                total_points += day_points['points']
                point_counts.append(day_points)

            # point_counts needs to be rotated so that the current day is last
            curr_day_num = time.localtime().tm_wday
            point_counts = point_counts[curr_day_num+1:] + point_counts[:curr_day_num+1]

            point_dict['point_counts'] = point_counts
            point_dict['total_points'] = total_points
            data.append(point_dict)

            id_index += 1

    # default is linear points
    else:
        for (full_name, uniqname, id) in ids:
            total_points = 0
            point_dict = {}
            point_dict['full_name'] = full_name
            point_dict['uniqname'] = uniqname
            point_counts = []
            for day_num in range(7):
                day_points = {}
                day_points['day'] = days[day_num]
                points = 0
                for pings in interact_dict[id][day_num].values():
                    points += pings
                    total_points += pings
                day_points['points'] = points
                point_counts.append(day_points)

            # point_counts needs to be rotated so that the current day is last
            curr_day_num = time.localtime().tm_wday
            point_counts = point_counts[curr_day_num+1:] + point_counts[:curr_day_num+1]

            point_dict['point_counts'] = point_counts
            point_dict['total_points'] = total_points
            data.append(point_dict)

    # Sort data by total points
    data = sorted(data, key=lambda record: record['total_points'], reverse=True)
    
    return json.dumps(data)

if __name__ == "__main__":
    app.run()
    #app.run(host="0.0.0.0")
