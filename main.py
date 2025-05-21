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
        "objects": [],
        "users": []
    }
    try:
        data = msg.split(":")
        ret["msgType"] = data[0]
        ret["rootTransform"] = data[1]
        
        rootMatrix = strToMatrix(data[1])
        inverseRootMatrix = np.linalg.inv(rootMatrix)

        for i in range(2, len(data)):
            object = data[i].split(";")            
            
            if object[0] == "User":
                u = {
                    "name": object[1],
                    "headPosition": object[2:5],
                    "headRotation": object[5:8],
                    "lhPosition": object[8:11],
                    "lhRotation": object[11:14],
                    "rhPosition": object[14:17],
                    "rhRotation": object[17:20],
                    "scale": object[20]
                }
                
                ret["users"].append(u)
            elif object[0] != '0':
                d = {
                    "id": object[0],
                    "typeTag": object[1],
                    # TODO: Active Boolean (not sent right now)
                    "active": "True",
                    "name": object[2],
                    "position": object[3:6], #localMatrix.flatten().tolist(),
                    "rotation": object[6:9],
                    "scale": object[9:12],           
                    "properties": {
                        "bool": object[12],
                        "float": object[13],
                        "color": [],
                        "intensity": "1",
                        "meshName": "",
                        "visible": "1",
                        "opacity": "1",
                        "clipName": "",
                        "looping": "0",
                        "isPlaying": "1",
                        "volume": "1",
                        "fov": "45"
                    }
                }
                
                # parse properties for each type
                if object[1] == "Mesh":
                    d["properties"]["meshName"] = object[14]
                    d["properties"]["visible"] = object[15]
                    d["properties"]["color"] = object[16:21] # this is sent as 5 values (RGBA + color space)
                    d["properties"]["transparency"] = object[21]
                    pass
                elif object[1] == "Lamp":
                    d["properties"]["color"] = object[14:19] # this is sent as 5 values (RGBA + color space)
                    d["properties"]["intensity"] = object[19]
                    pass
                elif object[1] == "Camera":
                    d["properties"]["fov"] = object[14]
                    pass
                elif object[1] == "Audio":
                    d["properties"]["clipName"] = object[14]
                    d["properties"]["looping"] = object[15]
                    d["properties"]["isPlaying"] = object[16]
                    d["properties"]["volume"] = object[17]
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

# Matrix to convert Resonite space → Unreal space (RH Z-up to LH Z-up)
conversion = np.array([
    [1, 0, 0, 0],  # Resonite X → Unreal Z
    [0, 1, 0, 0],  # Resonite Y → Unreal Y
    [0, 0, -1, 0], # Resonite Z → Unreal -Z
    [0, 0, 0, 1]
])
def resoniteToUnrealMatrix(resoMat):
    unrealMat = conversion @ M_resonite @ np.linalg.inv(conversion)
    return unrealMat

def limitEulerRanges(eulerArr):
    if (eulerArr[0] > 180): eulerArr[0] -= 360
    if (eulerArr[0] < 180): eulerArr[0] += 360

    if (eulerArr[1] > 180): eulerArr[1] -= 360
    if (eulerArr[1] < 180): eulerArr[1] += 360

    if (eulerArr[2] > 180): eulerArr[2] -= 360
    if (eulerArr[2] < 180): eulerArr[2] += 360

    return eulerArr
    
def resoniteToUnrealPosition(resoPos):
    return [resoPos[0] * 100, resoPos[2] * 100, resoPos[1] * 100]
    
def resoniteToUnrealEuler(resoEuler):
    return [resoEuler[0], resoEuler[2], resoEuler[1]]

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
            obj_active = obj["active"]
            
            #transform_values = obj["transform"]
            
            position = obj["position"]
            rotation = np.array(obj["rotation"]).astype(np.float)
            scale = obj["scale"]

            #transform_values = obj["transform"]
            # convert Resonite to Unreal positions/rotations/scale
            uPos = [float(position[0]) * 100, -float(position[2]) * 100, float(position[1]) * 100] #flip y
            rotation = limitEulerRanges(rotation)
            uEuler = [rotation[0], rotation[2], rotation[1]] #flip x & z rotation
            uScale = [scale[0], scale[2], scale[1]]
            
            # Create message with object name in the address
            obj_msg = osc_message_builder.OscMessageBuilder(address=f"/object/{obj_name}")
            
            # Add all object data to the message
            obj_msg.add_arg(obj_id)
            obj_msg.add_arg(obj_type)
            obj_msg.add_arg(obj_active)
            obj_msg.add_arg(obj_name)
            
            for val in uPos:
                obj_msg.add_arg(str(val))
            for val in uEuler:
                obj_msg.add_arg(str(val))
            for val in uScale:
                obj_msg.add_arg(val)
                
            # wildcards
            obj_msg.add_arg(obj["properties"]["bool"])
            obj_msg.add_arg(obj["properties"]["float"])
            
            # per type properties
            if obj_type == "Mesh":
                obj_msg.add_arg(obj["properties"]["meshName"])
                obj_msg.add_arg(obj["properties"]["visible"])
                for val in obj["properties"]["color"]:
                    obj_msg.add_arg(val)
                obj_msg.add_arg(obj["properties"]["transparency"])
                pass
            elif obj_type == "Lamp":
                for val in obj["properties"]["color"]:
                    obj_msg.add_arg(val)
                obj_msg.add_arg(obj["properties"]["intensity"])
                pass
            elif obj_type == "Camera":
                obj_msg.add_arg(obj["properties"]["fov"])
                pass
            elif obj_type == "Audio":
                obj_msg.add_arg(obj["properties"]["clipName"])
                obj_msg.add_arg(obj["properties"]["looping"])
                obj_msg.add_arg(obj["properties"]["isPlaying"])
                obj_msg.add_arg(obj["properties"]["volume"])
                pass
            
            messages.append(obj_msg.build())
        # Process users
        for usr in data["users"]:
            usr_name = usr["name"]
            
            # parse to arrays
            usr_hPos = np.array(usr["headPosition"]).astype(np.float)
            usr_lhPos = np.array(usr["lhPosition"]).astype(np.float)
            usr_rhPos = np.array(usr["rhPosition"]).astype(np.float)
            
            usr_hRot = limitEulerRanges(np.array(usr["headRotation"]).astype(np.float))
            usr_lhRot = limitEulerRanges(np.array(usr["lhRotation"]).astype(np.float))
            usr_rhRot = limitEulerRanges(np.array(usr["rhRotation"]).astype(np.float))
            
            # convert to unreal space
            usr_hPos = resoniteToUnrealPosition(usr_hPos)
            usr_lhPos = resoniteToUnrealPosition(usr_hPos)
            usr_lhPos = resoniteToUnrealPosition(usr_hPos)
            
            usr_hRot = resoniteToUnrealEuler(usr_hRot)
            usr_hRot = resoniteToUnrealEuler(usr_hRot)
            usr_hRot = resoniteToUnrealEuler(usr_hRot)
            
            # build message            
            usr_msg = osc_message_builder.OscMessageBuilder(address=f"/user/{usr_name}")
            
            usr_msg.add_arg(usr_name)
            
            for val in usr_hPos:
                usr_msg.add_arg(str(val))
            for val in usr_hRot:
                usr_msg.add_arg(str(val))
            for val in usr_lhPos:
                usr_msg.add_arg(str(val))
            for val in usr_lhRot:
                usr_msg.add_arg(str(val))
            for val in usr_rhPos:
                usr_msg.add_arg(str(val))
            for val in usr_rhRot:
                usr_msg.add_arg(str(val))

            usr_msg.add_arg(usr["scale"])
                
            messages.append(obj_msg.build())
            
    except Exception as e:
        print("error creating OSC Messages: {0}".format(e))
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
            print("Message received")#: {0}".format(jsonMsgDump))
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
