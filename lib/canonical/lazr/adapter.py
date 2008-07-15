# Copyright 2008 Canonical Ltd.  All rights reserved.
"""
Useful functions for dealing with Zope adapters.
"""

__metaclass__ = type
__all__ = ['nearest_adapter', 'nearest_context_with_adapter']

from zope.component import queryAdapter
from canonical.launchpad.webapp.publisher import canonical_url_iterator


def nearest_context_with_adapter(obj, interface, name=u''):
    """Return the tuple (context, adapter) of the nearest object up the
    canonical url chain that has an adapter of the type given.

    This might be an adapter for the object given as an argument.

    Return (None, None) if there is no object that has such an adapter
    in the url chain.

    """
    for current_obj in canonical_url_iterator(obj):
        adapter = queryAdapter(current_obj, interface, name=name)
        if adapter is not None:
            return (current_obj, adapter)
    return (None, None)


def nearest_adapter(obj, interface, name=u''):
    """Return the adapter of the nearest object up the canonical url chain
    that has an adapter of the type given.

    This might be an adapter for the object given as an argument.

    :return None: if there is no object that has such an adapter in the url
        chain.

    This will often be used with an interface of IFacetMenu, when looking up
    the facet menu for a particular context.

    """
    context, adapter = nearest_context_with_adapter(obj, interface, name=name)
    # Will be None, None if not found.
    return adapter
