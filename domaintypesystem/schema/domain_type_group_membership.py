# THIS FILE HAS BEEN GENERATED AUTOMATICALLY BY capnpy
# do not edit by hand
# generated on 2018-02-24 20:52

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

class DomainTypeGroupMembership(_Struct): pass
DomainTypeGroupMembership.__name__ = 'DomainTypeGroupMembership'


#### DEFINITIONS ####

@DomainTypeGroupMembership.__extend__
class DomainTypeGroupMembership(_Struct):
    __static_data_size__ = 0
    __static_ptrs_size__ = 2
    
    
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
    def multicast_group(self):
        # no union check
        return self._read_str_data(8)
    
    def get_multicast_group(self):
        return self._read_str_data(8, default_=b"")
    
    def has_multicast_group(self):
        ptr = self._read_fast_ptr(8)
        return ptr != 0
    
    @staticmethod
    def __new(struct_name=None, multicast_group=None):
        builder = _SegmentBuilder()
        pos = builder.allocate(16)
        builder.alloc_text(pos + 0, struct_name)
        builder.alloc_data(pos + 8, multicast_group)
        return builder.as_string()
    
    def __init__(self, struct_name=None, multicast_group=None):
        _buf = DomainTypeGroupMembership.__new(struct_name, multicast_group)
        self._init_from_buffer(_buf, 0, 0, 2)
    
    def shortrepr(self):
        parts = []
        if self.has_struct_name(): parts.append("struct_name = %s" % _text_repr(self.get_struct_name()))
        if self.has_multicast_group(): parts.append("multicast_group = %s" % _text_repr(self.get_multicast_group()))
        return "(%s)" % ", ".join(parts)

_DomainTypeGroupMembership_list_item_type = _StructItemType(DomainTypeGroupMembership)


_extend_module_maybe(globals(), modname=__name__)