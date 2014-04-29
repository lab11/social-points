
import IPy
import json
import sys
import sqlite3
import time

try:
    import socketIO_client as sioc
except ImportError:
    print('Could not import the socket.io client library.')
    print('sudo pip install socketIO-client')
    sys.exit(1)

import logging
logging.basicConfig()

SOCKETIO_HOST      = 'inductor.eecs.umich.edu'
SOCKETIO_PORT      = 8082
SOCKETIO_NAMESPACE = 'stream'

DEBUG = False

query = {'profile_id': '4wbddZCSIj'}

# query the last week's worth of opo data if requested. This takes a couple
#   minutes to run
if len(sys.argv) == 2 and sys.argv[1] == 'repopulate':
    print("Repopulating database...")
    SOCKETIO_PORT = 8083
    query['time'] = 7*24*3600*1000
    DEBUG = True

class stream_receiver (sioc.BaseNamespace):
    last_clean_time = 0

    def on_reconnect (self):
        if 'time' in query:
            del query['time']
        stream_namespace.emit('query', query)

    def on_connect (self):
        stream_namespace.emit('query', query)

    def on_disconnect (self):
        print("Disconnected!!!")

    def on_data (self, *args):
        pkt = args[0]

        # Determine the name of this packet data
        full_name = ''
        if ('full_name' in pkt):
            full_name = pkt['full_name']
        else:
            full_name = pkt['id']

        uniqname = ''
        if ('uniqname' in pkt):
            uniqname = pkt['uniqname']
        else:
            uniqname = pkt['uniqname']

        # Handle data received by this packet
        if DEBUG:
            print(time.ctime(pkt['adjusted_last_full_timestamp']))

        update_database(full_name, uniqname, pkt)

        if (time.time() - self.last_clean_time > 24*3600):
            clean_database()
            self.last_clean_time = time.time()

def update_database(full_name, uniqname, pkt):

    try:
        # Log interaction in database if unique
        data_tuple = (pkt['id'], pkt['last_heard_id'], pkt['adjusted_last_full_timestamp'], pkt['range'])
        name_tuple = (full_name, uniqname, pkt['id'])
        cur.execute("INSERT OR IGNORE INTO Interactions VALUES(?, ?, ?, ?)", data_tuple)
        cur.execute("INSERT OR REPLACE INTO Identifications VALUES(?, ?, ?)", name_tuple)
        con.commit()
    except sqlite3.Error, e:
        if con:
            con.rollback()
            con.close()
        print "Sqlite Error: %s:" % e.args[0]
        sys.exit(1)

def clean_database():
    #print("Cleaning Database")
    week_ago = int(time.time() - 7*24*3600)
    try:
        cur.execute("DELETE FROM Interactions WHERE Time < ?", (week_ago,))
        con.commit()
    except sqlite3.Error, e:
        if con:
            con.rollback()
            con.close()
        print "Sqlite Error: %s:" %e.args[0]
        sys.exit(1)

con = sqlite3.connect('db/opo_data.db')
cur = con.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS Interactions(Id TEXT, Last_Heard_Id TEXT, Time INT, Range INT, UNIQUE(Id, Last_Heard_Id, Time))")
cur.execute("CREATE TABLE IF NOT EXISTS Identifications(Full_Name TEXT, Uniqname TEXT, Id TEXT, UNIQUE(Id))")

socketIO = sioc.SocketIO(SOCKETIO_HOST, SOCKETIO_PORT)
stream_namespace = socketIO.define(stream_receiver,
    '/{}'.format(SOCKETIO_NAMESPACE))

try:
    while True:
        socketIO.wait()
        print("Was ejected from wait... Trying again")
finally:
    if con:
        con.close()

