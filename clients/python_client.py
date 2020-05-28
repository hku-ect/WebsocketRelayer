#!/usr/bin/evn python3
from socketIO_client import SocketIO, LoggingNamespace
### For debugging uncomment this
#import logging
#logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
#logging.basicConfig()

def on_connect(*args):
    print('connect')

def on_disconnect(*args):
    print('disconnect')

def on_reconnect():
    print('reconnect')

def on_message_event(*args):
    for v in args:
        print('message_event:', v)

socketIO = SocketIO('localhost', 3000, LoggingNamespace)
socketIO.on('connect', on_connect)
socketIO.on('disconnect', on_disconnect)
socketIO.on('reconnect', on_reconnect)

# Listen
socketIO.on('message_event', on_message_event)
socketIO.emit('message_event', 1)
socketIO.emit('message_event', 2)
socketIO.wait(seconds=1)
#socketIO.wait()  # Use this to wait forever

# Stop listening
socketIO.off('message_event')
socketIO.emit('message_event', 3)
socketIO.wait(seconds=1)

# Listen only once
socketIO.once('message_event', on_message_event)
socketIO.emit('message_event', 4)  # Activate on_message_event
socketIO.emit('message_event', 5)  # Ignore
socketIO.wait(seconds=1)
