import json
import numpy as np
import logging
from typing import Dict, List, Any

from flask import Flask, render_template
from flask_sock import Sock
from pythonosc import osc_message_builder
from pythonosc import osc_message
from pythonosc import osc_packet
from pythonosc import osc_bundle
import gevent
from gevent import pywsgi
from gevent import monkey
gevent.monkey.patch_all()

app = Flask(__name__)
app.debug = True
sockets = Sock(app)

clients = set()

def oscToResonite(oscmsg):
    return "dit is een bericht voor resonite"
    
def parse_osc_bundle_from_bytes(bundle_data):
    """
    Parse an OSC bundle from raw bytes
    
    Args:
        bundle_data (bytes): Raw OSC bundle data
        
    Returns:
        tuple: (timestamp, messages) where messages is a list of parsed OSC messages
    """
    try:
        # Parse the bundle from bytes
        bundle = osc_bundle.OscBundle(bundle_data)
        
        messages = []
        for content in bundle:
            if isinstance(content, osc_message.OscMessage):
                print(f"  Address: {content.address}")
                print(f"  Arguments: {content.params}")
                messages.append({
                    'address': content.address,
                    'params': content.params
                })
        
        return messages            
    except Exception as e:
        print(f"Error parsing bundle: {e}")
        return None

class UDPServer(gevent.server.DatagramServer):

    def handle(self, data, address): # pylint:disable=method-hidden
        #print('%s: got %r' % (address[0], data))
        #self.socket.sendto(('Received %s bytes' % len(data)).encode('utf-8'), address)
        try:
            # oscm = osc_message.OscMessage(data)
            # bundle parse_nested_bundle
            oscMessages = parse_osc_bundle_from_bytes(data)
        except Exception as e:
            print("Osc error:", e)
        else:
            for oscm in oscMessages:
                print("OSC received:", oscm.address)
                #print("OSC received:", oscm.address, oscm.params)
                todel = []
                for c in clients:
                    try:
                        c.send(oscToResonite(oscm))
                    except Exception as e:
                        print("Clients seems gone, error is:", e)
                        todel.append(c)
                for c in todel:
                    clients.discard(c)

@sockets.route('/echo')
def echo_socket(ws):
    clients.add(ws)
    while ws.connected:
        #msg = ws.receive()
        message = {"hello": "world" }
        # JSON formatted data
        jsonMsgDump = json.dumps(message, indent=2)

        todel = []
        if message:
            print("Message received: {0}".format(jsonMsgDump))

            # forward to other clients
            for c in clients:
                try:
                    c.send(jsonMsgDump)
                except Exception as e:
                    print("Clients seems gone, error is:", e)
                    todel.append(c)
            for c in todel:
                clients.discard(c)
            gevent.sleep(10)

@app.route('/')
def hello():
    return render_template('index.html')


if __name__ == "__main__":
    # Uncomment to run from gevent
    logging.basicConfig(level=logging.INFO)
    udpserver = UDPServer(":9000")
    udpserver.start()
    print("OSC server running on port 9000, WS server on *:5001/echo")
    server = pywsgi.WSGIServer(('', 5001), app)
    server.serve_forever()

