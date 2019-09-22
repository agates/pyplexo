FROM pypy:3
MAINTAINER Alecks Gates <agates@mail.agates.io>

RUN apt -qq update \
&& apt -qqy install --no-install-recommends capnproto dbus \
&& rm -rf /var/lib/apt/lists/ \
&& dbus-uuidgen > /var/lib/dbus/machine-id \
&& mkdir -p /opt/app \
&& addgroup --system appuser \
&& adduser --system --home /opt/app --ingroup appuser appuser \
&& chown -R appuser:appuser /opt/app \
&& pip install --no-cache-dir pipenv

COPY . /opt/app

WORKDIR /opt/app

# Install the package and dependencies from Pipfile.lock as system-wide
RUN pipenv install --system --deploy --ignore-pipfile \
&& pip install . \
&& rm -rf ~/.cache/

USER appuser

#EXPOSE 5555

CMD ["pypy3", "examples/basic_handle_any.py"]