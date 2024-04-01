TODO:

- [×] 03/07 报文需要去重：类型、HTTP方法、URL相同、源和目的IP对称且时间戳相差不超过100的（注：未加入“源和目的IP对称”这个条件但暂时实现去重）
- [ ] 03/08 筛选出来的报文……真能按时间戳相近来列入怀疑名单吗



packet 字段：
['_PickleType', '__all_slots__', '__bool__', '__bytes__', '__class__', '__class_getitem__', '__contains__', '__deepcopy__', '__delattr__', '__delitem__', '__dict__', '__dir__', '__div__', '__doc__', '__eq__', '__format__', '__ge__', '__getattr__', '__getattribute__', '__getitem__', '__getstate__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__iter__', '__iterlen__', '__le__', '__len__', '__lt__', '__module__', '__mul__', '__ne__', '__new__', '__nonzero__', '__orig_bases__', '__parameters__', '__rdiv__', '__reduce__', '__reduce_ex__', '__repr__', '__rmul__', '__rtruediv__', '__setattr__', '__setitem__', '__setstate__', '__signature__', '__sizeof__', '__slots__', '__str__', '__subclasshook__', '__truediv__', '__weakref__', '_answered', '_defrag_pos', '_do_summary', '_is_protocol', '_name', '_overload_fields', '_pkt', '_resolve_alias', '_show_or_dump', '_superdir', 'add_parent', 'add_payload', 'add_underlayer', 'aliastypes', 'answers', 'build', 'build_done', 'build_padding', 'build_ps', 'canvas_dump', 'class_default_fields', 'class_default_fields_ref', 'class_dont_cache', 'class_fieldtype', 'class_packetfields', 'clear_cache', 'clone_with', 'command', 'comment', 'copy', 'copy_field_value', 'copy_fields_dict', 'decode_payload_as', 'default_fields', 'default_payload_class', 'delfieldval', 'deprecated_fields', 'direction', 'dispatch_hook', 'display', 'dissect', 'dissection_done', 'do_build', 'do_build_payload', 'do_build_ps', 'do_dissect', 'do_dissect_payload', 'do_init_cached_fields', 'do_init_fields', 'dst', 'explicit', 'extract_padding', 'fields', 'fields_desc', 'fieldtype', 'firstlayer', 'fragment', 'from_hexcap', 'get_field', 'getfield_and_val', 'getfieldval', 'getlayer', 'guess_payload_class', 'hashret', 'haslayer', 'hide_defaults', 'init_fields', 'iterpayloads', 'lastlayer', 'layers', 'lower_bonds', 'match_subclass', 'mysummary', 'name', 'original', 'overload_fields', 'overloaded_fields', 'packetfields', 'parent', 'payload', 'payload_guess', 'pdfdump', 'post_build', 'post_dissect', 'post_dissection', 'post_transforms', 'pre_dissect', 'prepare_cached_fields', 'psdump', 'raw_packet_cache', 'raw_packet_cache_fields', 'remove_parent', 'remove_payload', 'remove_underlayer', 'route', 'self_build', 'sent_time', 'setfieldval', 'show', 'show2', 'show_indent', 'show_summary', 'sniffed_on', 'sprintf', 'src', 'summary', 'svgdump', 'time', 'type', 'underlayer', 'upper_bonds', 'wirelen']


关于时间戳：
这个时间戳看起来像是一个 Unix 时间戳，但是它的长度比通常的 Unix 时间戳要长。这可能是因为它是以微秒（而不是秒）为单位的。
Unix 时间戳是从 1970 年 1 月 1 日（UTC）开始计算的秒数。如果这个时间戳是以微秒为单位的，那么你可以通过将它除以 1,000,000 来将它转换为以秒为单位的时间戳。

前10位数字相同的时间戳表示的是同一秒内的时间戳