FROM python:3.8-alpine as base
FROM base as builder
RUN apk add --no-cache git gcc g++ musl-dev linux-headers yaml-dev
COPY requirements.txt /
RUN pip3 install --prefix=/usr/local --no-warn-script-location -r /requirements.txt --verbose

FROM base
LABEL maintainer="Andreas Thienemann" \
      description="iCal to KNX Gateway"

COPY --from=builder /usr/local /usr/local

COPY . /app
WORKDIR /app

CMD ["python3", "-u", "knxcal.py"]
