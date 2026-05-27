#include "DFRobot_OxygenSensor.h"
#include "DHT.h"

#define Oxygen_IICAddress ADDRESS_3
#define COLLECT_NUMBER  10
DFRobot_OxygenSensor oxygen;

#define DHT22_PIN 2
DHT dht22(DHT22_PIN, DHT22);

//---------------------------------------- PARAMETERS FOR CONTROL
const int ledPin = 8;     // pin for realy control of the Nitrogen valve
const int fanPin = 6;     // pin for the relay control of the fan in the chamber
int incomingByte;
float controlEnabled = 0;
float setlevel = 21.0;


// -------------------------------------------------------- Valve control
bool valveActive = false;
unsigned long valveStartTime = 0;
int skipCount = 0;

//------------------- parameter that can be adjusted for finer tuning of oxygen control------------------------
const unsigned long valveInterval = 1000;  // 1 second valve open time
const int skipReadings = 3;  // how many oxygen readings to skip *after valve turns off*

float thres = 2;    //--------- default value is updated line 68 -------- threshold fixed for stronger oxygen control (reduce downtime + works also for setlevels close to 0) 
//  threshold = 4 works for setlevel 5 and 10
//  threshold = 0.2  works for setlevel 1
bool limit = true;  // ---------------- logical variable to differentiate control logic (higher than threshold)



void setup() {
  Serial.begin(9600);
  pinMode(ledPin, OUTPUT);
  pinMode(fanPin, OUTPUT);
  while(!oxygen.begin(Oxygen_IICAddress)){
    delay(1000);
  }
  dht22.begin();
}


void loop(){
  float oxygenData = oxygen.getOxygenData(COLLECT_NUMBER);
  delay(1000);

  // Read humidity and temperature
  float humi  = dht22.readHumidity();
  float tempC = dht22.readTemperature();
  float tempF = dht22.readTemperature(true);

  if (isnan(humi) || isnan(tempC) || isnan(tempF)) {
    Serial.println("Failed to read from DHT22 sensor!");
  } else {
    Serial.print(oxygenData);
    Serial.print(" "); 
    Serial.print(humi);
    Serial.print(" "); 
    Serial.println(tempC);
  }

  // ------------------------ Handle serial input
  if (Serial.available() > 0) {
    incomingByte = Serial.read();

    if (incomingByte == 'F') {
      while (Serial.available() < sizeof(float));
      float receivedValue;
      Serial.readBytes((char*)&receivedValue, sizeof(receivedValue));
      setlevel = receivedValue;
      if (setlevel > 4){
        thres = 4;
      }else{
        thres = 0.2;
      }
    } else if (incomingByte == 'H') {
      controlEnabled = 1;
    } else if (incomingByte == 'L') {
      controlEnabled = 0;
      digitalWrite(ledPin, LOW);
      // ---------------- resetting logic control variables
      valveActive = false;      
      skipCount = 0;
    } else if (incomingByte == 'O') {
      digitalWrite(fanPin, HIGH);  // start the fan  (when power plugged in but no control the fan should start (NC circuit))
    } else if (incomingByte == 'N') {
      digitalWrite(fanPin, LOW);  // stop the fan
    }
  }

  // ---------------------- Control logic for higher values of oxygen
  if (controlEnabled == 1 && oxygenData > setlevel + thres) {
    digitalWrite(ledPin, HIGH);      // open valve (when power plugged in but no control the nitrogen should not flow (NO circuit)) (now we might need to invert the logic (I swapped NO and NC on the relay))
    valveActive = false;             
    skipCount = 0;                   
    limit = false;
  }
  
  if (oxygenData <= setlevel + thres) { //---------- condition to activate control logic with pause
    limit = true;
  }

  // ---------------------- Turn off valve after interval
  if (valveActive && (millis() - valveStartTime >= valveInterval)) {
    digitalWrite(ledPin, LOW);       // Close the valve
    valveActive = false;
    skipCount = skipReadings;        // Begin skipping control checks
  }

  // ---------------------- Skip control logic during pause period (once the valve opened and closed the first time, it waits before maybe opening again if the oxygen level is too high) 
  if (skipCount > 0) {    
    skipCount--;
    return;
  }

  // ---------------------- Control logic for normal oxygen overshoot
  if (controlEnabled == 1 && oxygenData > setlevel && !valveActive && limit) {
    digitalWrite(ledPin, HIGH);      // Open valve
    valveActive = true;
    valveStartTime = millis();       // Start 1s timer
  }
}
