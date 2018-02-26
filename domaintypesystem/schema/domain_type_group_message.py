# THIS FILE HAS BEEN GENERATED AUTOMATICALLY BY capnpy
# do not edit by hand
# generated on 2018-02-25 13:02

from capnpy import ptr as _ptr
from capnpy.struct_ import Struct as _Struct
from capnpy.struct_ import check_tag as _check_tag
from capnpy.struct_ import undefined as _undefined
from capnpy.enum import enum as _enum, fill_enum as _fill_enum
from capnpy.enum import BaseEnum as _BaseEnum
from capnpy.type import Types as _Types
from capnpy.segment.builder import SegmentBuilder as _SegmentBuilder
from capnpy.list import List as _List
from capnpy.list import PrimitiveItemType as _PrimitiveItemType
from capnpy.list import BoolItemType as _BoolItemType
from capnpy.list import TextItemType as _TextItemType
from capnpy.list import StructItemType as _StructItemType
from capnpy.list import EnumItemType as _EnumItemType
from capnpy.list import VoidItemType as _VoidItemType
from capnpy.list import ListItemType as _ListItemType
from capnpy.util import text_repr as _text_repr
from capnpy.util import float32_repr as _float32_repr
from capnpy.util import float64_repr as _float64_repr
from capnpy.util import extend_module_maybe as _extend_module_maybe
from capnpy.util import check_version as _check_version
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
    __static_data_size__ = 1
    __static_ptrs_size__ = 2
    
    
    __tag__ = DomainTypeGroupMessage__tag__
    __tag_offset__ = 0
    
    def is_struct(self):
        return self._read_data_int16(0) == 0
    def is_query(self):
        return self._read_data_int16(0) == 1
    
    @property
    def host_id(self):
        # no union check
        return self._read_str_data(0)
    
    def get_host_id(self):
        return self._read_str_data(0, default_=b"")
    
    def has_host_id(self):
        ptr = self._read_fast_ptr(0)
        return ptr != 0
    
    @property
    def struct(self):
        self._ensure_union(0)
        return self._read_str_data(8)
    
    def get_struct(self):
        return self._read_str_data(8, default_=b"")
    
    def has_struct(self):
        ptr = self._read_fast_ptr(8)
        return ptr != 0
    
    @property
    def query(self):
        self._ensure_union(1)
        return None
    
    @staticmethod
    def __new(host_id=None, struct=_undefined, query=_undefined):
        builder = _SegmentBuilder()
        pos = builder.allocate(24)
        anonymous__curtag = None
        builder.alloc_data(pos + 8, host_id)
        if struct is not _undefined:
            anonymous__curtag = _check_tag(anonymous__curtag, 'struct')
            builder.write_int16(0, 0)
            builder.alloc_data(pos + 16, struct)
        if query is not _undefined:
            anonymous__curtag = _check_tag(anonymous__curtag, 'query')
            builder.write_int16(0, 1)
        return builder.as_string()
    
    def __init__(self, host_id=None, struct=_undefined, query=_undefined):
        _buf = DomainTypeGroupMessage.__new(host_id, struct, query)
        self._init_from_buffer(_buf, 0, 1, 2)
    
    @classmethod
    def new_struct(cls, host_id=None, struct=None):
        buf = DomainTypeGroupMessage.__new(host_id=host_id, struct=struct, query=_undefined)
        return cls.from_buffer(buf, 0, 1, 2)
    
    @classmethod
    def new_query(cls, host_id=None, query=None):
        buf = DomainTypeGroupMessage.__new(host_id=host_id, query=query, struct=_undefined)
        return cls.from_buffer(buf, 0, 1, 2)
    
    def shortrepr(self):
        parts = []
        if self.has_host_id(): parts.append("host_id = %s" % _text_repr(self.get_host_id()))
        if self.is_struct() and (self.has_struct() or
                                  not True):
            parts.append("struct = %s" % _text_repr(self.get_struct()))
        if self.is_query(): parts.append("query = %s" % "void")
        return "(%s)" % ", ".join(parts)

_DomainTypeGroupMessage_list_item_type = _StructItemType(DomainTypeGroupMessage)


_extend_module_maybe(globals(), modname=__name__)