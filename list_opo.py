
import IPy
import json
import sys

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

        # Handle data received by this packet
        update_database(name, pkt)

def update_database(name, pkt):
    # Access database to see record at this name

    # Determine if this is a new social interaction
    if 
        # Update time decay of social points

    else:
        # Update social points for each user in this interaction

socketIO = sioc.SocketIO(SOCKETIO_HOST, SOCKETIO_PORT)
stream_namespace = socketIO.define(stream_receiver,
    '/{}'.format(SOCKETIO_NAMESPACE))

socketIO.wait()
