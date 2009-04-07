# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Interfaces for OpenID consumer functions."""

__metaclass__ = type
__all__ = ['IOpenIDConsumerStoreFactory']

from zope.interface import Interface

class IOpenIDConsumerStoreFactory(Interface):
    """Factory to create OpenIDConsumerStore instances."""

    def __call__():
        """Create a LaunchpadOpenIDStore instance."""
