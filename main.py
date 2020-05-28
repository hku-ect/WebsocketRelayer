from flask import Flask, render_template
from flask_socketio import SocketIO
from flask import request

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vnkdjnfjknfl1232#'
socketio = SocketIO(app)

# track number of clients connected (currently including conductor)
clients = 0

def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')

@app.route('/')
def sessions():
    return render_template('session.html')

@app.route('/conductor')
def conductor():
    return render_template('conductor.html')

@socketio.on('connect')
def on_connect():
    print("Client connect event")
    global clients
    clients += 1
    socketio.emit('connect', {'event': 'Connected', 'clientid': request.sid });

@socketio.on('disconnect')
def on_disconnect():
    global clients
    clients -= 1
    socketio.emit('disconnect', {'event': 'Disconnected', 'clientid': request.sid });
    print( 'Client disconnected', request.sid )

@socketio.on('message_event')
def on_message_event(msg):
    print('received message: {}'.format(msg))
    socketio.emit("message_event", { 'clientid': request.sid, 'message': msg });

@socketio.on_error_default
def default_error_handler(e):
    print("######### ERROR HANDLER #########")
    print(e)
    print(request.event["message"]) # "my error event"
    print(request.event["args"])    # (data,)
    print("######### END ERROR HANDLER #####")


if __name__ == '__main__':
    socketio.run(app, host= '0.0.0.0', port=3000, debug=True)
