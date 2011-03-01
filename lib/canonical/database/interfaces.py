# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from zope.interface import Interface
from zope.interface.common.interfaces import IRuntimeError
from zope.schema import Int

class IRequestExpired(IRuntimeError):
    """A RequestExpired exception is raised if the current request has
    timed out.
    """

# XXX 2007-02-09 jamesh:
# This derrived from sqlos.interfaces.ISQLObject before hand.  I don't
# think it is ever used though ...
class ISQLBase(Interface):
    """An extension of ISQLObject that provides an ID."""
    id = Int(title=u"The integer ID for the instance")

