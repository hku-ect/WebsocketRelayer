from flask import Flask, render_template
from flask_sock import Sock
from pythonosc import osc_message_builder
from typing import Dict, List, Any
import zmq
import json
import numpy as np

app = Flask(__name__)
app.debug = True
sockets = Sock(app)

clients = set()
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5555")

def msg2json(msg):
    ret = {
        "msgType": 0,
        "rootTransform": "",
        "objects": []
    }
    try:
        data = msg.split(":")
        ret["msgType"] = data[0]
        ret["rootTransform"] = data[1]
        
        rootMatrix = strToMatrix(data[1])
        inverseRootMatrix = np.linalg.inv(rootMatrix)

        for i in range(2, len(data)):
            object = data[i].split(";")
            
            globalMatrix = valToMatrix(object[3:19])
            localMatrix = np.matmul(inverseRootMatrix, globalMatrix)
            
            d = {
                "id": object[0],
            	"typeTag": object[1],
                # TODO: Active Boolean (not sent right now)
            	"name": object[2],
                "transform": localMatrix.flatten().tolist()
                "properties": {
                    "bool": object[20],
                    "float": object[21],
                    "color": [],
                    "intensity": 1,
                    "meshName": "",
                    "visible": 1,
                    "opacity": 1,
                    "clipName": "",
                    "looping": 0,
                    "isPlaying": 1,
                    "volume": 1,
                    "fov": 45
                }
            }
            
            # parse properties for each type
            if object[1] == "Mesh":
                d["properties"]["meshName"] = object[22]
                d["properties"]["visible"] = object[23]
                d["properties"]["color"] = object[24:29] # this is sent as 5 values (RGBA + color space)
                d["properties"]["transparency"] = object[30]
                pass
            elif object[1] == "Lamp":
                d["properties"]["color"] = object[22:27] # this is sent as 5 values (RGBA + color space)
                d["properties"]["intensity"] = object[27]
                pass
            elif object[1] == "Camera":
                d["properties"]["fov"] = object[22]
                pass
            elif object[1] == "AudioSource":
                d["properties"]["clipName"] = object[22]
                d["properties"]["looping"] = 0 # NOT CURRENTLY SENT
                d["properties"]["isPlaying"] = object[23] # this is sent as 5 values (RGBA + color space)
                d["properties"]["volume"] = object[24]
                pass
            
            ret["objects"].append(d)
    except Exception as e:
        print("error parsing message: {}".format(e))
    finally:
        return ret

def strToMatrix(transform_str):
    values = transform_str.strip('[]').split(';')
    return valToMatrix(values)
    
def valToMatrix(transform_values):
    float_values = [float(val) for val in transform_values]
    
    # Create a 4x4 identity matrix
    matrix = np.identity(4)
    
    if len(float_values) == 12:
        # Fill the first 3 rows
        matrix[0, 0:4] = float_values[0:4]
        matrix[1, 0:4] = float_values[4:8]
        matrix[2, 0:4] = float_values[8:12]
        # The 4th row remains [0,0,0,1]
    elif len(float_values) == 16:
        # Handle full 4x4 matrix for compatibility
        matrix = np.array(float_values).reshape(4, 4)
    else:
        print(f"Warning: Expected 12 or 16 values in transform, got {len(float_values)}")
        # Try to use whatever values we have
        if len(float_values) >= 12:
            matrix[0, 0:4] = float_values[0:4]
            matrix[1, 0:4] = float_values[4:8]
            matrix[2, 0:4] = float_values[8:12]
    
    return matrix
    
def parse_to_osc(data: Dict[str, Any]) -> List[osc_message_builder.OscMessageBuilder]:
    messages = []
    
    try:
        # Root transform message
        root_msg = osc_message_builder.OscMessageBuilder(address="/root")
        rootValues = data["rootTransform"].strip('[]').split(';')
        rootFloats = [float(val) for val in rootValues]
        for val in rootFloats:
            root_msg.add_arg(val)
        messages.append(root_msg.build())
        
        # Process each object
        for obj in data["objects"]:        
            obj_id = obj["id"]
            obj_type = obj["typeTag"]
            obj_name = obj["name"]
            transform_values = obj["transform"]  # Get the 16 transform values (indices 3-18)
            
            # Create message with object name in the address
            obj_msg = osc_message_builder.OscMessageBuilder(address=f"/object/{obj_name}")
            
            # Add all object data to the message
            obj_msg.add_arg(obj_id)
            obj_msg.add_arg(obj_type)
            obj_msg.add_arg(obj_name)
            for val in transform_values:
                obj_msg.add_arg(val)
            
            if obj_type == "Mesh":
                obj_msg.add_arg(obj["meshName"])
                obj_msg.add_arg(obj["visible"])
                obj_msg.add_arg(obj["color"])
                obj_msg.add_arg(obj["transparency"])
                pass
            elif obj_type == "Lamp":
                obj_msg.add_arg(obj["color"])
                obj_msg.add_arg(obj["intensity"])
                pass
            elif obj_type == "Camera":
                obj_msg.add_arg(obj["fov"])
                pass
            elif obj_type == "AudioSource":
                obj_msg.add_arg(obj["clipName"])
                obj_msg.add_arg(obj["looping"])
                obj_msg.add_arg(obj["isPlaying"])
                obj_msg.add_arg(obj["volume"])
                pass
            
            messages.append(obj_msg.build())
    except Exception as e:
        print("error creating OSC Messages: {}".format(e))
    finally:
        return messages

@sockets.route('/echo')
def echo_socket(ws):
    clients.add(ws)
    while ws.connected:
        msg = ws.receive()
        
        # Message formatted in a JSON-like structure
        message = msg2json(msg)
        # JSON formatted data
        jsonMsgDump = json.dumps(message, indent=2)
        # OSC message based on the relevant parts of the data as well
        oscMessages = parse_to_osc(message)
        for oscMessage in oscMessages:
            socket.send(oscMessage.dgram)
        
        todel = []
        if message:
            print("Message received: {0}".format(jsonMsgDump))
            # forward over zmq
            # socket.send(jsonMsgDump.encode())
            
            # forward to other clients
            for c in clients:
                try:
                    c.send(jsonMsgDump)
                except Exception as e:
                    print("Clients seems gone, error is:", e)
                    todel.append(c)
            for c in todel:
                clients.discard(c)


@app.route('/')
def hello():
    return render_template('index.html')


if __name__ == "__main__":
    # Uncomment to run from gevent
    from gevent import pywsgi, monkey
    import logging
    logging.basicConfig(level=logging.INFO)
    monkey.patch_all()
    #from werkzeug.serving import run_with_reloader
    #from werkzeug.debug import DebuggedApplication
    #if app.debug:
    #    application = DebuggedApplication(app)
    #else:
    server = pywsgi.WSGIServer(('', 5000), app)
    server.serve_forever()

    # Run just from flask, comment when run from gevent
    #app.run()
