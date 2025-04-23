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
            	"name": object[2],
                "transform": localMatrix.flatten().tolist()
                #"Position": data[3:5],
                #"Rotation": data[6:8],
                #"Scale": data[7:9]
            }
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
        messages.append(root_msg)
        
        # Process each object
        for obj in data["objects"]:        
            obj_id = obj[0]
            obj_type = obj[1]
            obj_name = obj[2]
            transform_values = obj[3:19]  # Get the 16 transform values (indices 3-18)
            
            # Create message with object name in the address
            obj_msg = osc_message_builder.OscMessageBuilder(address=f"/object/{obj_name}")
            
            # Add all object data to the message
            obj_msg.add_arg(obj_id)
            obj_msg.add_arg(obj_type)
            obj_msg.add_arg(obj_name)
            for val in transform_values:
                obj_msg.add_arg(val)
                
            messages.append(obj_msg)
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
            socket.send(oscMessage)
        
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
