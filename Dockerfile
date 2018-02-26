FROM jamiehewland/alpine-pypy
MAINTAINER Alecks Gates <agates@mail.agates.io>

RUN apk update
RUN apk add dbus
RUN dbus-uuidgen > /var/lib/dbus/machine-id

ADD . .
RUN pip install -r requirements.txt

EXPOSE 5555

ENTRYPOINT ["pypy3", "main.py"]