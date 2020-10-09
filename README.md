# knxcal
iCal to KNX Gateway

Usage instructions
------------------

# checkout code to your local machine
git clone https://github.com/ixs/knxcal.git
cd knxcal
# build a docker image
docker build --tag knxcal:latest .
# run the application as a docker image
docker run --rm -it knxcal:latest
