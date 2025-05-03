#main.py

import eventlet
eventlet.monkey_patch()

from .web_server import app, socketio

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
