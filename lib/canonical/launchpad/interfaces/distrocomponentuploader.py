# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces including and related to IDistroComponentUploader."""

__metaclass__ = type

__all__ = ['IDistroComponentUploader']

from zope.interface import Interface, Attribute


class IDistroComponentUploader(Interface):
    """A grant of upload rights to a person or team, applying to a distribution
    and a specific component therein.
    """

    id = Attribute("The ID of this particular upload grant.")

    distribution = Attribute("The distribution this grant is related to.")
    component = Attribute("The component this grant is related to.")
    uploader = Attribute("The uploader or uploaders this grant applies to.")

    def __contains__(person):
        """Determine if a given person is in the set of uploaders."""


    # XXX: dsilvers,stevea: 20051012: Refactor this to use ICrowd some time.
    # Bug 3081
