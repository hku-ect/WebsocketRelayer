from flask import Flask, render_template
from flask_sockets import Sockets


app = Flask(__name__)
app.debug = True
sockets = Sockets(app)

clients = set()

@sockets.route('/echo')
def echo_socket(ws):
    clients.add(ws)
    while not ws.closed:
        message = ws.receive()
        todel = []
        print("Message received: {0}".format(message))
        for c in clients:
            try:
                c.send(message)
            except Exception as e:
                print("Clients seems gone", e)
                todel.append(c)
        #ws.send(message)
        for c in todel:
            clients.discard(c)


@app.route('/')
def hello():
    return render_template('index.html')


if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    import logging
    logging.basicConfig(level=logging.INFO)

    #from werkzeug.serving import run_with_reloader
    #from werkzeug.debug import DebuggedApplication
    #if app.debug:
    #    application = DebuggedApplication(app)
    #else:
    application = app
    server = pywsgi.WSGIServer(('', 5000), application, handler_class=WebSocketHandler)
    server.serve_forever()
#     app.run()
