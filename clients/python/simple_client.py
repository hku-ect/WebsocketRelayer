from websocket import create_connection
ws = create_connection("ws://pong.hku.nl:5000/echo")
print("Sending 'Hello, from simple_client")
ws.send("Hello, from simple_client")
print("Sent")
print("Receiving...")
result =  ws.recv()
print("Received '%s'" % result)
ws.close()
