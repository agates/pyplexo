@0xb1c8ca3cc964cf2b;

struct DomainTypeGroupMessage {
    hostId @0 :Data;

    union {
        struct @1: Data;
        query @2: Void;
    }
}