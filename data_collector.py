
import IPy
import json
import sys
import sqlite3

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

query = {'profile_id': '4wbddZCSIj'}

class stream_receiver (sioc.BaseNamespace):
    def on_reconnect (self):
        if 'time' in query:
            del query['time']
        stream_namespace.emit('query', query)

    def on_connect (self):
        stream_namespace.emit('query', query)

    def on_data (self, *args):
        pkt = args[0]

        # Determine the name of this packet data
        name = ''
        if ('name' in pkt):
            name = pkt['name']
        else:
            name = pkt['tx_id']

        print(pkt)
        # Handle data received by this packet
        update_database(name, pkt)

def update_database(name, pkt):

    try:
        # Log interaction in database if unique
        data_tuple = (pkt['tx_id'], pkt['last_tx_id'], pkt['full_time'])
        name_tuple = (name, pkt['tx_id'])
        cur.execute("INSERT OR IGNORE INTO Interactions VALUES(?, ?, ?)", data_tuple)
        cur.execute("INSERT OR REPLACE INTO Identifications VALUES(?, ?)", name_tuple)
        con.commit()
    except sqlite3.Error, e:
        if con:
            con.rollback()

        print "Sqlite Error: %s:" % e.args[0]
        sys.exit(1)
        
        if con:
            con.close()

con = sqlite3.connect('opo_data.db')
cur = con.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS Interactions(Interactor TEXT, Interactee TEXT, Time INT, UNIQUE(Interactor, Interactee, Time))")
cur.execute("CREATE TABLE IF NOT EXISTS Identifications(Name TEXT, Id TEXT, UNIQUE(Name, Id))")

socketIO = sioc.SocketIO(SOCKETIO_HOST, SOCKETIO_PORT)
stream_namespace = socketIO.define(stream_receiver,
    '/{}'.format(SOCKETIO_NAMESPACE))

try:
    socketIO.wait()
finally:
    if con:
        con.close()

