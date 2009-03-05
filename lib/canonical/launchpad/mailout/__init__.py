# Copyright 2008 Canonical Ltd.  All rights reserved.

from zope.security.proxy import isinstance as zope_isinstance
from lazr.enum import BaseItem

def value_string(item):
    """Return a unicode string representing an SQLObject value."""
    if item is None:
        return '(not set)'
    elif zope_isinstance(item, BaseItem):
        return item.title
    else:
        return unicode(item)


def text_delta(instance_delta, delta_names, state_names, interface):
    """Return a textual delta for a Delta object.

    A list of strings is returned.

    Only modified members of the delta will be shown.

    :param instance_delta: The delta to generate a textual representation of.
    :param delta_names: The names of all members to show changes to.
    :param state_names: The names of all members to show only the new state
        of.
    :param interface: The Zope interface that the input delta compared.
    """
    output = []
    indent = ' ' * 4

    # Fields for which we have old and new values.
    for field_name in delta_names:
        delta = getattr(instance_delta, field_name, None)
        if delta is None:
            continue
        title = interface[field_name].title
        old_item = value_string(delta['old'])
        new_item = value_string(delta['new'])
        output.append("%s%s: %s => %s" % (indent, title, old_item, new_item))
    for field_name in state_names:
        delta = getattr(instance_delta, field_name, None)
        if delta is None:
            continue
        title = interface[field_name].title
        if output:
            output.append('')
        output.append('%s changed to:\n\n%s' % (title, delta))
    return '\n'.join(output)


def append_footer(main, footer):
    """Append a footer to an email, following signature conventions.

    If there is no footer, do nothing.
    If there is already a signature, append an additional footer.
    If there is no existing signature, append '-- \n' and a footer.

    :param main: The main content, which may have a signature.
    :param footer: An additional footer to append.
    :return: a new version of main that includes the footer.
    """
    if footer == '':
        footer_separator = ''
    elif '\n-- \n' in main:
        footer_separator = '\n'
    else:
        footer_separator = '\n-- \n'
    return ''.join((main, footer_separator, footer))
