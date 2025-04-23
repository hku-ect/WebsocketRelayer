from flask import Flask, render_template
from flask_sock import Sock
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
        "rootTransform": ""
        "objects": []
    }
    try:
        data = msg.split(":")
        ret["msgType"] = data[0]
        ret["rootTransform"] = data[1]
        
        rootMatrix = strToMatrix(data[1])
        inverseRootMatrix = np.linalg.inv(parent_matrix)

        for i in range(2, len(data)):
            object = data[i].split(";")
            
            globalMatrix = strToMatrix(object[3:19])
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
        return json.dumps(ret, indent=2)

def strToMatrix(transform_str):
    values = transform_str.strip('[]').split(';')
    float_values = [float(val) for val in values]
    
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

@sockets.route('/echo')
def echo_socket(ws):
    clients.add(ws)
    while ws.connected:
        msg = ws.receive()
        message = msg2json(msg)
        todel = []
        if message:
            print("Message received: {0}".format(message))
            # forward over zmq
            socket.send(message.encode())
            
            # forward to other clients
            for c in clients:
                try:
                    c.send(message)
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
