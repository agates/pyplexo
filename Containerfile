FROM pypy:3.7-buster

RUN apt -qq update \
    && apt -qqy install --no-install-recommends capnproto dbus libzmq3-dev libpgm-dev \
    && rm -rf /var/lib/apt/lists/ \
    && dbus-uuidgen > /etc/machine-id \
    && mkdir -p /opt/app \
    && addgroup --system appuser \
    && adduser --system --home /opt/app --ingroup appuser appuser \
    && chown -R appuser:appuser /opt/app \
    && pip install --no-cache-dir pipenv

COPY . /opt/app

WORKDIR /opt/app

# Install the package and dependencies from Pipfile.lock as system-wide
RUN pipenv install --system --deploy --ignore-pipfile \
    && pip install --force --no-binary :all: pyzmq~=19.0 \
    && pip install .

USER appuser

EXPOSE 5560/udp
EXPOSE 5561/udp

CMD ["pypy3", "examples/plexus/basic_send.py"]
