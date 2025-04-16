from flask import Flask, render_template
from flask_sock import Sock
import zmq
import json

app = Flask(__name__)
app.debug = True
sockets = Sock(app)

clients = set()
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5555")

def msg2json(msg):
    ret = ""
    try:
        data = msg.split(";")
        msgtype = data[0]
        d = {
            "id": data[0],
            "TypeTag": data[1],
            "Name": data[2],
            "Position": data[3:5],
            "Rotation": data[6:8],
            "Scale": data[7:9]
        }
        ret = json.dumps(d)
    except Exception as e:
        print("error parsing message: {}".format(e))
    finally:
        return ret

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
