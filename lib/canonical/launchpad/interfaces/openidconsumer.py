# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Interfaces for OpenID consumer functions."""

__metaclass__ = type
__all__ = ['IOpenIDConsumerStore']

from zope.interface import Interface


class IOpenIDConsumerStore(Interface):
    """An OpenID association and nonce store for Launchpad."""
