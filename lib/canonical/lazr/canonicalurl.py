# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Useful functions for dealing with Zope adapters.
"""

__metaclass__ = type
__all__ = ['nearest_adapter', 'nearest_context_with_adapter']

from zope.component import queryAdapter

# XXX mars 2008-07-17
# This function should be moved into lazr.canonicalurl.
# See bug #185958.
from canonical.launchpad.webapp.publisher import canonical_url_iterator


def nearest_context_with_adapter(obj, interface, name=u''):
    """Find the nearest adapter in the url chain between obj and interface.

    The function looks upward though the canonical url chain and returns a
    tuple of (object, adapter).

    :return (None, None): if there is no object that has such an adapter
        in the url chain.
    """
    for current_obj in canonical_url_iterator(obj):
        adapter = queryAdapter(current_obj, interface, name=name)
        if adapter is not None:
            return (current_obj, adapter)
    return (None, None)


def nearest_adapter(obj, interface, name=u''):
    """Find the nearest adapter in the url chain between obj and interface.

    The function looks upward though the canonical url chain and returns
    the first adapter it finds.

    :return None: if there is no object that has such an adapter in the url
        chain.
    """
    context, adapter = nearest_context_with_adapter(obj, interface, name=name)
    # Will be None, None if not found.
    return adapter
