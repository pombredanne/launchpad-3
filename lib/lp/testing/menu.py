# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Useful helper functions used for testing menus."""

__metaclass__ = type

from zope.component import getMultiAdapter

from canonical.lazr.testing.menus import make_fake_request
from canonical.launchpad.webapp.publisher import canonical_url


def check_menu_links(menu):
    context = menu.context
    for link in menu.iterlinks():
        if link.target.startswith('/'):
            # The context is not the context of this target.
            continue
        if '?' in link.target:
            view_name, _args = link.target.split('?')
        else:
            view_name = link.target
        url = canonical_url(context, view_name=view_name)
        request = make_fake_request(url)
        try:
            view = getMultiAdapter((context, request), name=view_name)
        except:
            return 'Bad link %s: %s' % (link.name, url)
    return True
