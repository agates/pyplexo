_This is a **highly experimental** project in a pre-alpha state.  Use at your own risk._

# Domain Type System
The [Domain Type System] (DTS) is the first draft and implementation of the concept of a flexible 
"decentralized type system."

## Goal

The goal of the project is to allow data structures to be shared across the network by their type instead
of server endpoints.  DTS receives a data structure and sends it to any interested parties subscribed to the data
structure's type.

It's currently used by and developed for a tiny sake brewing operation.  It has been created solely for this purpose but
will hopefully be extended over time.

The development of this project has enabled us to plug in new hardware sensors and data logging devices without the need
to reconfigure multiple projects across a variety of hardware.

## Limitations

Currently the project only works over local multicast (with a different multicast group per type).  The plan is to
support pluggable transport implementations over other networks: TCP, HTTP, Web Sockets, and potentially other message
passing implementations such as MQTT, ZeroMQ, nanomsg, Amazon SQS, etc.

It's also tied to the [capnproto] data interchage format, though there's nothing keeping it from being data interchange
agnostic in the future.  There's no reason it can't support the likes of [JSON], [CBOR], [Ion], [MessagePack],
[Protocol Buffers], [XML], [Python Pickles], or even raw bytes, for example.

Only small data structures can be sent right now (anything that fits into a typical <1500 byte packet, minus DTS
overhead). This is only because large amounts of data weren't needed for our purposes during development, but this will
change in the future.

## Running in Docker

As this project currently requires multicast, you either need to route multicast traffic to the appropriate docker
interface or run the docker container with `--net=host`.

The following command enables routing of the multicast CIDR block DTS will use to the default docker interface:

    # ip route add 239.255.0.0/16 dev docker0

Without additional setup, this will affect the container's routing to other networks (including the internet).  If this
is problematic, check out [pipework](https://github.com/jpetazzo/pipework) for many well-tested use-cases.

[pimd](https://github.com/troglobit/pimd/), a multicast router, may also be of interest.

[domain type system]: https://gitlab.com/agates/domain-type-system
[capnproto]: https://capnproto.org/
[json]: https://json.org/
[cbor]: http://cbor.io/
[ion]: http://amzn.github.io/ion-docs/docs/spec.html
[messagepack]: https://msgpack.org/
[protocol buffers]: https://developers.google.com/protocol-buffers/
[xml]: https://www.w3.org/XML/
[python pickles]: https://docs.python.org/3.5/library/pickle.html