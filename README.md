# WebsocketRelayer

A simple websocket server which relays to all clients written in Python using Flask.

Just connect to the server and any message you sent will be received by all connected clients.

# TL;DR

```
$ git clone https://github.com/hku-ect/WebsocketRelayer.git
Cloning into 'WebsocketRelayer'...
...
$ cd WebsocketRelayer/
$ python3 -m venv mypythondir
$ . mypythondir/bin/activate
$ pip install flask flask-socketio eventlet
Collecting flask
  Using cached https://files.pythonhosted.org/packages/9b/93/628509b8d5dc749656a9641f4caf13540e2cdec85276964ff8f43bbb1d3b/Flask-1.1.1-py2.py3-none-any.whl
...
$ python3 main.py
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 239-841-434
(27896) wsgi starting up on http://0.0.0.0:5000
```

# Installation
You will need the eventlet, flask and flask-socketio dependency, see below. Inside the repository directory run the server:

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
pip install flask flask-socketio eventlet
```

## Deploy on Heroku

You will need a heroku account with the heroku CLI tools installed!

* Create a new app in heroku (You will need the name)
* Login in the terminal: `heroku login`
* Add the project to heroku: `heroku git:remote -a {your-project-name}` This will add a remote to the git repo
* Finally upload the repo to heroku: `git push heroku master`
* Test the deploy at your heroku name: `https://{your-project-name}.herokuapp.com/`

