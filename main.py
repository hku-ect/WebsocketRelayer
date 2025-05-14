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
            
            #globalMatrix = valToMatrix(object[3:19])
            #localMatrix = np.matmul(inverseRootMatrix, globalMatrix)
            #localMatrix = resoniteToUnrealMatrix(localMatrix)
            #localMatrix = fix_rotation_in_4x4_matrix(localMatrix)
            
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
                d["properties"]["looping"] = "0" # NOT CURRENTLY SENT
                d["properties"]["isPlaying"] = object[15]
                d["properties"]["volume"] = object[16]
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

def fix_rotation_in_4x4_matrix(matrix, source_order='xyz', target_order='zyx'):
    """
    Fix rotation in a 4x4 transformation matrix while preserving position and scale.
    
    Args:
        matrix: 4x4 transformation matrix (numpy array)
        source_order: Euler angle order in the source system (e.g., 'xyz' for Resonite)
        target_order: Euler angle order in the target system (e.g., 'zyx' for Unreal)
    
    Returns:
        4x4 transformation matrix with the corrected rotation
    """
    # Make a copy to avoid modifying the original
    result_matrix = np.copy(matrix)
    
    # Extract components
    rotation_matrix = matrix[:3, :3]
    translation = matrix[:3, 3]
    
    # Extract scales from the rotation matrix columns
    scale_x = np.linalg.norm(rotation_matrix[:, 0])
    scale_y = np.linalg.norm(rotation_matrix[:, 1])
    scale_z = np.linalg.norm(rotation_matrix[:, 2])
    scales = np.array([scale_x, scale_y, scale_z])
    
    # Normalize the rotation matrix to remove scaling
    normalized_rotation = np.zeros((3, 3))
    for i in range(3):
        normalized_rotation[:, i] = rotation_matrix[:, i] / scales[i]
    
    # Ensure the matrix is a proper rotation matrix (orthogonal with determinant 1)
    # This helps prevent issues with slightly non-orthogonal matrices
    u, _, vh = np.linalg.svd(normalized_rotation)
    proper_rotation = u @ vh
    
    # Handle reflection matrices (determinant -1)
    if np.linalg.det(proper_rotation) < 0:
        u[:, -1] *= -1
        proper_rotation = u @ vh
    
    # Create rotation object from the proper rotation matrix
    r = R.from_matrix(proper_rotation)
    
    # Get source system Euler angles
    source_euler = r.as_euler(source_order, degrees=True)
    
    # Print for debugging
    print(f"Source euler angles ({source_order}): {source_euler}")
    
    # Convert to target system using the same angles but different convention
    target_r = R.from_euler(target_order, source_euler, degrees=True)
    corrected_rotation = target_r.as_matrix()
    
    # Reapply scales to the corrected rotation matrix
    scaled_rotation = np.zeros((3, 3))
    for i in range(3):
        scaled_rotation[:, i] = corrected_rotation[:, i] * scales[i]
    
    # Reconstruct the 4x4 matrix with the corrected rotation
    result_matrix[:3, :3] = scaled_rotation
    
    # Print the expected Euler angles in the target system
    target_euler = target_r.as_euler(target_order, degrees=True)
    print(f"Target euler angles ({target_order}): {target_euler}")
    
    return result_matrix

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
            rotation = obj["rotation"]
            scale = obj["scale"]
            
            # Create message with object name in the address
            obj_msg = osc_message_builder.OscMessageBuilder(address=f"/object/{obj_name}")
            
            # Add all object data to the message
            obj_msg.add_arg(obj_id)
            obj_msg.add_arg(obj_type)
            obj_msg.add_arg(obj_active)
            obj_msg.add_arg(obj_name)
            
            for val in position:
                obj_msg.add_arg(val)
            for val in rotation:
                obj_msg.add_arg(val)
            for val in scale:
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
