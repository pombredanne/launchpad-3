# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Session interfaces."""

__metaclass__ = type
__all__ = ['ISessionStormClass']


from zope.interface import Interface


class ISessionStormClass(Interface):
    """Marker interface for Session Storm database classes."""
    pass
