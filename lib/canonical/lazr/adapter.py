# Copyright 2008 Canonical Ltd.  All rights reserved.
"""
Useful functions for dealing with Zope adapters.
"""

__metaclass__ = type
__all__ = ['nearest_adapter', 'nearest_context_with_adapter']


from canonical.launchpad.webapp.publisher import canonical_url_iterator


def nearest_context_with_adapter(obj, interface):
    """Find the nearest adapter in the url chain between obj and interface.

    The function looks upward though the canonical url chain and returns a
    tuple of (object, adapter).

    :return (None, None): if there is no object that has such an adapter
        in the url chain.
    """
    for current_obj in canonical_url_iterator(obj):
        adapter = interface(current_obj, None)
        if adapter is not None:
            return (current_obj, adapter)
    return (None, None)


def nearest_adapter(obj, interface):
    """Find the nearest adapter in the url chain between obj and interface.

    The function looks upward though the canonical url chain and returns
    the first adapter it finds.

    This will often be used with an interface of IFacetMenu, when looking up
    the facet menu for a particular context.

    :return None: if there is no object that has such an adapter in the url
        chain.
    """
    context, adapter = nearest_context_with_adapter(obj, interface)
    # Will be None, None if not found.
    return adapter
