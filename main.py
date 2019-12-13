from flask import Flask, render_template
from flask_socketio import SocketIO
from flask import request

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vnkdjnfjknfl1232#'
socketio = SocketIO(app)

bla = 1

def messageReceived(methods=['GET', 'POST']):
	print('message was received!!!')

@app.route('/')
def sessions():
    return render_template('session.html')

@app.route('/conductor')
def conductor():
    return render_template('conductor.html')

@socketio.on('connect')
def test_connect():
    socketio.emit('registration', {'event': 'Connected', 'clientid': request.sid })

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(msg):
    global bla
    bla += 1
    print('received message: {}'.format(msg))
    msg['bla'] = bla
    socketio.emit("bla", msg);

@socketio.on('registration')
def handle_json(msg):
    print('received data: {}'.format( msg ))
    socketio.emit("registration", msg);

@socketio.on_error_default
def default_error_handler(e):
    print("######### ERROR HANDLER #########")
    print(e)
    print(request.event["message"]) # "my error event"
    print(request.event["args"])    # (data,)
    print("######### END ERROR HANDLER #####")

if __name__ == '__main__':
    socketio.run(app, host= '0.0.0.0', debug=True)
