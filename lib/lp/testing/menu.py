# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Useful helper functions used for testing menus."""

__metaclass__ = type

from canonical.launchpad.webapp.publisher import canonical_url


def check_menu_links(menu):
    context = menu.context
    for link in menu.iterlinks():
        if link.target.startswith(('/', 'http://')):
            # The context is not the context of this target.
            continue
        if '?' in link.target:
            view_name, _args = link.target.split('?')
        else:
            view_name = link.target
        if view_name == '':
            view_name = None
        try:
            canonical_url(context, view_name=view_name, rootsite=link.site)
        except Exception:
            return 'Bad link %s: %s' % (link.name, canonical_url(context))
    return True
