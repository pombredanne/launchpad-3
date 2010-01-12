# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Common build interfaces."""

__metaclass__ = type

__all__ = ['IBuildBase']

from zope.interface import Interface

class IBuildBase(Interface):
    pass
