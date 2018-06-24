@0xb1c8ca3cc964cf2b;

# Nanoseconds since the epoch.
using TimePointInNs = UInt64;

struct DomainTypeGroupMessage {
    structName @0 :Text;
    hostId @1 :Data;
    timestamp @2 :TimePointInNs;

    union {
        struct @3: Data;
        query @4: Text;
    }

    instanceId @5: UInt64;
}