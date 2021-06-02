// using Websockets 0.1b from Lasse Steenbock Vestergaard
import websockets.*;

WebsocketClient wsc;

int now;
boolean newEllipse;

void setup(){
  size(200,200);
  
  newEllipse=true;
  
  wsc= new WebsocketClient(this, "ws://pong.hku.nl:5000/echo");
  now=millis();
}

void draw(){
  if(newEllipse){
    ellipse(random(width),random(height),10,10);
    newEllipse=false;
  }
    
  if(millis()>now+5000){
    wsc.sendMessage("Hello from Processing");
    now=millis();
  }
}

void webSocketEvent(String msg){
 println(msg);
 newEllipse=true;
}
