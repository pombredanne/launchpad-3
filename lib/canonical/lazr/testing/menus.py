# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for testing menus."""

__metaclass__ = type
__all__ = [
    'summarise_tal_links',
    'make_fake_request',
    ]


from zope.security.proxy import isinstance as zope_isinstance
from zope.security.management import endInteraction, newInteraction

from canonical.lazr.utils import safe_hasattr

from canonical.launchpad.webapp import urlsplit
from canonical.launchpad.webapp.servers import LaunchpadTestRequest


def summarise_tal_links(links):
    """List the links and their attributes in the dict or list.

    :param links: A dictionary or list of menu links returned by
        `canonical.launchpad.webapp.tales.MenuAPI`.
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


def make_fake_request(url, traversed_objects=None):
    """Return a fake request object for menu testing.

    :param traversed_objects: A list of objects that becomes the request's
        traversed_objects attribute.
    """
    url_parts = urlsplit(url)
    server_url = '://'.join(url_parts[0:2])
    path_info = url_parts[2]
    request = LaunchpadTestRequest(
        SERVER_URL=server_url,
        PATH_INFO=path_info)
    request._traversed_names = path_info.split('/')[1:]
    request.traversed_objects = traversed_objects
    # After making the request, setup a new interaction.
    endInteraction()
    newInteraction(request)
    return request
