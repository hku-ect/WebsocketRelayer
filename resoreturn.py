import sys
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

class ResoObject(object):

    def __init__(self, name, string) -> None:
        self.name = name
        self._string = string
        self.parse()

    def _parse_value(self, vs):
        name, val = vs.split("=")
        val = float(val)
        return (name, val)

    def unreal2ResonitePosition(self, resoPos):
        return [resoPos[0] / 100, resoPos[2] / 100, -resoPos[1] / 100]

    def unreal2ResoniteEuler(self, resoEuler):
        return [-resoEuler[0], resoEuler[2], resoEuler[1]]


    def parse(self):
        spl = self._string.split(" ")
        self.obj = spl[0]
        self.uid = spl[1]
        self.pos = (self._parse_value(spl[2])[1],
                    self._parse_value(spl[3])[1],
                    self._parse_value(spl[4])[1])
        self.pos = self.unreal2ResonitePosition(self.pos)
        self.rot = (self._parse_value(spl[5])[1],
                    self._parse_value(spl[6])[1],
                    self._parse_value(spl[7])[1])
        self.rot = self.unreal2ResoniteEuler(self.rot)

    def encode(self):
        s = ";".join([self.obj, self.uid, self.name, str(self.pos[0]), str(self.pos[1]), str(self.pos[2]),
                        str(self.rot[0]), str(self.rot[1]), str(self.rot[2])])
        return s

#resobj = ResoObject("hoofd", "Catwalk_Walk 5FF2F2C74B9506396D713194548BC815 X=3631.734 Y=1331.797 Z=-1.371 X=-116.006 Y=5.844 Z=-109.783")
#print(resobj.encode())
#sys.exit()

def oscToResonite(oscmsg):
    resos = oscmsg.params[0]
    name = oscmsg.address.split("/")[2]
    resoobj = ResoObject(name, resos)
    return resoobj.encode()
    
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
            messages.append(content)
            #if isinstance(content, osc_message.OscMessage):
            #    print(f"  Address: {content.address}")
            #    print(f"  Arguments: {content.params}")
            #    messages.append({
            #        'address': content.address,
            #        'params': content.params
            #    })
        
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

