# Copyright 2008 Canonical Ltd.  All rights reserved.

from canonical.lazr import DBItem


def valueString(item):
    if item is None:
        return '(not set)'
    elif getattr(item, '__class__', None) == DBItem:
        return item.title
    else:
        return item


def deltaLines(instance_delta, delta_names, state_names, interface):
    delta_lines = []
    indent = ' ' * 4

    # Fields for which we have old and new values.
    for field_name in delta_names:
        delta = getattr(instance_delta, field_name, None)
        if delta is None:
            continue
        title = interface[field_name].title
        old_item = valueString(delta['old'])
        new_item = valueString(delta['new'])
        delta_lines.append(
            "%s%s: %s => %s" % ( indent, title, old_item, new_item))
    for field_name in state_names:
        delta = getattr(instance_delta, field_name, None)
        if delta is None:
            continue
        title = interface[field_name].title
        if delta_lines:
            delta_lines.append('')
        delta_lines.append('%s changed to:\n\n%s' % (title, delta))
    return delta_lines
