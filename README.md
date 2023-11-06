# pyplexo

*pyplexo* is the Python implementation of *plexo*. It aims to be an opinionated, reactive, schema-driven, distributed,
and
strongly-typed message passing framework with messages as types. Any type of data interchange format is supported and
can be transmitted both to in-process and inter-process listeners.

## plexo

*plexo* is an architecture in which data is transmitted across the network in a way where the receiver is able to
understand the correct type to decode the data into. It does so by assigning type names to a predefined namespace to
create a topic for receivers to subscribe to.

While *plexo* is relatively stable and in production use between Python and Rust (
see [podping.cloud](https://github.com/Podcastindex-org/podping.cloud)
and [podping-hivewriter](https://github.com/Podcastindex-org/podping-hivewriter)), the paradigm remains experimental.
Contributions and suggestions are encouraged.

## Why does this exist?

The goal of the project is to allow data structures to be shared across the network by their type instead of server
endpoints.  *plexo* implementations receive data structures and sends them to any interested parties subscribed to the
data structure's type.

It was originally created and developed for a tiny sake brewing operation. The development of this project enabled us to
plug in new hardware sensors and data logging devices without the need to reconfigure multiple projects across a variety
of hardware.

This was born out of a frustration of spending too much time writing data transformation and validation layers with
unstructured and/or weakly typed data (JSON without schemas) across multiple languages.  *plexo* tries to solve this
problem without controlling the entire stack while avoiding protocol implementation details such as HTTP "REST" APIs.

## Examples

Check the [examples](examples) for how to use the library -- particularly [axon/inprocess](examples/axon/inprocess) for
multiple examples of codec options and [axon/tcp_pair](examples/axon/tcp_pair) for an example of how to send a python
class between two networked python processes with pickle or JSON. Note that, while supplying the pickle codec is
required, the *plexus* is smart enough to avoid the expensive process of encoding/decoding for in-process receivers;
codecs are only used for external transmission where serialization is required.

[ganglion/plexo_multicast](examples/ganglion/plexo_multicast) provides a basic example of sending a python class
across the network over multicast. Each type in is assigned a dedicated multicast address within the `239.255.0.0/16`
CIDR block as a means to provide generalized, zero configuration network communication without saturating a single
socket with unnecessary traffic. An adaptation of the Paxos consensus algorithm is used for the network to agree on
which type is assign to which multicast group.
