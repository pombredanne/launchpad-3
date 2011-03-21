# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Recipe build interfaces."""

__metaclass__ = type

__all__ = [
    'IRecipeBuildRecordSet',
    ]

from zope.interface import (
    Interface,
    )


class IRecipeBuildRecordSet(Interface):
    """Interface representing a set of recipe build records."""

    def findCompletedDailyBuilds(epoch_days=30):
        """Find the recently completed daily builds.

        :param epoch_days: only find builds completed in last epoch_days
        days. If None, return all completed builds.
        """
