# WebsocketRelayer

A simple websocket server which relays to all clients written in Python using Flask.

Just connect to the server and any message you sent will be received by all connected clients.



# Example

You will need the flask and socketio dependency, see below. Inside the repositiry directory run the server:

```
python3 main.py
```

## Use a virtual environment to customize a Python setup

First create an environment directory in the current directory:
```
python3 -m venv mypythondir
```
Then activate the Python environment for your session:
```
. mypythondir/bin/activate
```
You can now use pip to install any dependencies you need. For example install Flask with SocketIO:
```
pip install flask flask-socketio
```
