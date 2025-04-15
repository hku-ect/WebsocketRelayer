from flask import Flask, render_template
from flask_sock import Sock


app = Flask(__name__)
app.debug = True
sockets = Sock(app)

clients = set()

@sockets.route('/echo')
def echo_socket(ws):
    clients.add(ws)
    while ws.connected:
        message = ws.receive()
        todel = []
        if message:
            print("Message received: {0}".format(message))
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
    #from gevent import pywsgi, monkey
    #import logging
    #logging.basicConfig(level=logging.INFO)
    #monkey.patch_all()
    ##from werkzeug.serving import run_with_reloader
    ##from werkzeug.debug import DebuggedApplication
    ##if app.debug:
    ##    application = DebuggedApplication(app)
    ##else:
    #server = pywsgi.WSGIServer(('', 5000), app)
    #server.serve_forever()

    # Run just from flask, comment when run from gevent
    app.run()
