# knxcal
iCal to KNX Gateway

Usage instructions
------------------

1. checkout code to your local machine
git clone https://github.com/ixs/knxcal.git
2. build a docker image
cd knxcal
docker build --tag knxcal:latest .
3.  run the application as a docker image
docker run --rm -it knxcal:latest
