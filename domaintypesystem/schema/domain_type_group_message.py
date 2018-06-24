# THIS FILE HAS BEEN GENERATED AUTOMATICALLY BY capnpy
# do not edit by hand
# generated on 2018-03-17 20:27

from capnpy.enum import BaseEnum as _BaseEnum
from capnpy.enum import fill_enum as _fill_enum
from capnpy.list import StructItemType as _StructItemType
from capnpy.segment.builder import SegmentBuilder as _SegmentBuilder
from capnpy.struct_ import Struct as _Struct
from capnpy.struct_ import check_tag as _check_tag
from capnpy.struct_ import undefined as _undefined
from capnpy.util import check_version as _check_version
from capnpy.util import extend_module_maybe as _extend_module_maybe
from capnpy.util import text_repr as _text_repr

__capnpy_version__ = '0.5.0'
_check_version(__capnpy_version__)

#### FORWARD DECLARATIONS ####

class DomainTypeGroupMessage(_Struct): pass
DomainTypeGroupMessage.__name__ = 'DomainTypeGroupMessage'
class DomainTypeGroupMessage__tag__(_BaseEnum):
    __members__ = ('struct', 'query',)
    @staticmethod
    def _new(x):
        return DomainTypeGroupMessage__tag__(x)
_fill_enum(DomainTypeGroupMessage__tag__)


#### DEFINITIONS ####

@DomainTypeGroupMessage.__extend__
class DomainTypeGroupMessage(_Struct):
    __static_data_size__ = 3
    __static_ptrs_size__ = 3
    
    
    __tag__ = DomainTypeGroupMessage__tag__
    __tag_offset__ = 8
    
    def is_struct(self):
        return self._read_data_int16(8) == 0
    def is_query(self):
        return self._read_data_int16(8) == 1

    @property
    def struct_name(self):
        # no union check
        return self._read_str_text(0)

    def get_struct_name(self):
        return self._read_str_text(0, default_=b"")

    def has_struct_name(self):
        ptr = self._read_fast_ptr(0)
        return ptr != 0
    
    @property
    def host_id(self):
        # no union check
        return self._read_str_data(8)
    
    def get_host_id(self):
        return self._read_str_data(8, default_=b"")
    
    def has_host_id(self):
        ptr = self._read_fast_ptr(8)
        return ptr != 0

    @property
    def timestamp(self):
        # no union check
        value = self._read_data(0, ord(b'Q'))
        if 0 != 0:
            value = value ^ 0
        return value
    
    @property
    def struct(self):
        self._ensure_union(0)
        return self._read_str_data(16)
    
    def get_struct(self):
        return self._read_str_data(16, default_=b"")
    
    def has_struct(self):
        ptr = self._read_fast_ptr(16)
        return ptr != 0
    
    @property
    def query(self):
        self._ensure_union(1)
        return self._read_str_text(16)

    def get_query(self):
        return self._read_str_text(16, default_=b"")

    def has_query(self):
        ptr = self._read_fast_ptr(16)
        return ptr != 0

    @property
    def instance_id(self):
        # no union check
        value = self._read_data(16, ord(b'Q'))
        if 0 != 0:
            value = value ^ 0
        return value
    
    @staticmethod
    def __new(struct_name=None, host_id=None, timestamp=0, struct=_undefined, query=_undefined, instance_id=0):
        builder = _SegmentBuilder()
        pos = builder.allocate(48)
        anonymous__curtag = None
        builder.alloc_text(pos + 24, struct_name)
        builder.alloc_data(pos + 32, host_id)
        builder.write_uint64(pos + 0, timestamp)
        if struct is not _undefined:
            anonymous__curtag = _check_tag(anonymous__curtag, 'struct')
            builder.write_int16(8, 0)
            builder.alloc_data(pos + 40, struct)
        if query is not _undefined:
            anonymous__curtag = _check_tag(anonymous__curtag, 'query')
            builder.write_int16(8, 1)
            builder.alloc_text(pos + 40, query)
        builder.write_uint64(pos + 16, instance_id)
        return builder.as_string()

    def __init__(self, struct_name=None, host_id=None, timestamp=0, struct=_undefined, query=_undefined, instance_id=0):
        _buf = DomainTypeGroupMessage.__new(struct_name, host_id, timestamp, struct, query, instance_id)
        self._init_from_buffer(_buf, 0, 3, 3)
    
    @classmethod
    def new_struct(cls, struct_name=None, host_id=None, timestamp=0, struct=None, instance_id=0):
        buf = DomainTypeGroupMessage.__new(struct_name=struct_name, host_id=host_id, timestamp=timestamp, struct=struct,
                                           instance_id=instance_id, query=_undefined)
        return cls.from_buffer(buf, 0, 3, 3)
    
    @classmethod
    def new_query(cls, struct_name=None, host_id=None, timestamp=0, query=None, instance_id=0):
        buf = DomainTypeGroupMessage.__new(struct_name=struct_name, host_id=host_id, timestamp=timestamp, query=query,
                                           instance_id=instance_id, struct=_undefined)
        return cls.from_buffer(buf, 0, 3, 3)
    
    def shortrepr(self):
        parts = []
        if self.has_struct_name(): parts.append("struct_name = %s" % _text_repr(self.get_struct_name()))
        if self.has_host_id(): parts.append("host_id = %s" % _text_repr(self.get_host_id()))
        parts.append("timestamp = %s" % self.timestamp)
        if self.is_struct() and (self.has_struct() or
                                  not True):
            parts.append("struct = %s" % _text_repr(self.get_struct()))
        if self.is_query() and (self.has_query() or
                                not False):
            parts.append("query = %s" % _text_repr(self.get_query()))
        parts.append("instance_id = %s" % self.instance_id)
        return "(%s)" % ", ".join(parts)

_DomainTypeGroupMessage_list_item_type = _StructItemType(DomainTypeGroupMessage)


_extend_module_maybe(globals(), modname=__name__)