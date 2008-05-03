# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Core implementation of the script to update personal standing."""

__metaclass__ = type
__all__ = [
    'UpdatePersonalStanding',
    ]


from zope.component import getUtility

from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.scripts.base import LaunchpadCronScript


class UpdatePersonalStanding(LaunchpadCronScript):
    """Update personal standings based on approved moderated messages.

    When a person who is not a member posts a message to a mailing list, their
    message will get held for moderator approval.  If their postings to three
    different lists are approved, they get their personal standing bumped from
    Unknown to Good.  This will allow them to post to mailing lists they are
    not a member of with no future holds on their messages.

    Note however that it takes approved posts to three different lists to bump
    standing.  Also, standing will only ever transition from Unknown to Good.
    If their current personal standing is not Unknown, nothing will change.
    """

    def main(self):
        """Main script entry point."""
        self.logger.info('Updating personal standings')
        getUtility(IPersonSet).updatePersonalStandings()
        self.txn.commit()
        self.logger.info('Done.')
