# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Recipe build interfaces."""

__metaclass__ = type

__all__ = [
    'IRecipeBuildRecord',
    'IRecipeBuildRecordSet',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )


class IRecipeBuildRecord(Interface):
    """A class containing recipe build information."""

    sourcepackage = Attribute('The source package.')

    recipe = Attribute('The recipe.')

    recipeowner = Attribute('The recipe owner.')

    archive = Attribute('The archive that was built.')

    most_recent_build_time = Attribute('The time of the most recent build.')


class IRecipeBuildRecordSet(Interface):
    """Interface representing a set of recipe build records."""

    def findCompletedDailyBuilds():
        """Find the completed daily builds..
        """
