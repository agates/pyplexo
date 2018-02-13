class DomainTypeSystem:
    def __init__(self):
        raise NotImplementedError


class DomainTypeSystemQuery:
    def __init__(self):
        raise NotImplementedError


class DomainTypeSystemResponse:
    def __init__(self):
        raise NotImplementedError


class DomainTypeSystemRegistration:
    def __init__(self, type):
        self.type = type

        # query for type on multicast address
        # if response, use existing multicast group for type
        # if no response, register multicast group for type

    def handle(self, handlers):
        raise NotImplementedError

    def send(self, struct):
        raise NotImplementedError
