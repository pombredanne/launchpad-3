# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Helpers for testing menus."""

__metaclass__ = type
__all__ = [
    'summarise_tal_links',
    ]


from zope.security.proxy import isinstance as zope_isinstance

from canonical.lazr.utils import safe_hasattr


def summarise_tal_links(links):
    """List the links and their attributes in the dict or list.

    :param links: A dictionary or list of menu links returned by
        `canonical.launchpad.tales.MenuAPI`.
    """
    is_dict = zope_isinstance(links, dict)
    if is_dict:
        keys = sorted(links)
    else:
        keys = links
    for link_name in keys:
        if is_dict:
            link = links[link_name]
        else:
            link = link_name
        print 'link %s' % link.name
        attributes = ('url', 'enabled', 'menu', 'selected', 'linked')
        for attrname in attributes:
            if not safe_hasattr(link, attrname):
                continue
            print '    %s:' % attrname, getattr(link, attrname)
