# knxcal
iCal to KNX Gateway

Docker Usage instructions
-------------------------

1. checkout code to your local machine
```
git clone https://github.com/ixs/knxcal.git
```
2. build a docker image
```
cd knxcal
docker build --tag knxcal:latest .
```
3.  run the application as a docker image
```
docker run --rm -it knxcal:latest
```

Native Usage instructions
-------------------------

1. checkout code to your local machine
```
git clone https://github.com/ixs/knxcal.git
```
2. ensure dependencies are installed
```
cd knxcal
pip3 install -r requirements.txt
```
3. run the application
```
./knxcal.py
```


Configuration
-------------

The configuration is done throught the knxcal.ini file.

Section [knxcal] (required)
* iCalURL: The URL to the iCal file
* eventName: What event to trigger on
* checkFrequency: How often do we check for new events, currently not used
* stateFile: The file that is used to keep state what event already got notified

Section [connection] (optional)
* type: Connection type to the KNX bus: auto, tunneling, routing
* gateway_ip: IP of the gateway, required for tunneling, optional otherwise
* gateway_port: UDP Port listening on the gateway, optional
* local_ip: The local IP to bind to, optional

Section [trigger*]
This defines the trigger for an event. Can exist multiple times, names must be unique though. e.g. trigger1, trigger99, triggerabc are all acceptable names, they just need to start with trigger.
* offset: Hours to event, when to trigger
* base: begin or end, count the offset from either end or beginning of the event.
* address: The KNX group address to notify
* dpt: The KNX data point type to send
* value: The KNX value to send