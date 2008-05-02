# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Core implementation of the script to update personal standing."""

__metaclass__ = type
__all__ = [
    'UpdatePersonalStanding',
    ]


from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    IMessageApprovalSet, PersonalStanding, PostedMessageStatus)
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
        approved = getUtility(IMessageApprovalSet).getHeldMessagesWithStatus(
            PostedMessageStatus.APPROVED)

        # Keep track of approved messages by person and mailing list.
        self.logger.info('Analyzing approved messages')
        by_person = {}
        for held_message in approved:
            # If the person's current standing is not Unknown, skip them.
            standing = held_message.posted_by.personal_standing
            if standing != PersonalStanding.UNKNOWN:
                continue

            # Create a set to hold all the mailing lists this person has an
            # approved message on, and make sure it contains this held
            # message's mailing list.
            mailing_lists = by_person.setdefault(
                held_message.posted_by, set())
            mailing_lists.add(held_message.mailing_list)

        # Now iterate over all of the person's approved messages.  If there
        # are approved messages to at least three different lists, bump the
        # standing to Good.  The person would not have gotten on this list
        # unless their standing is already Unknown.
        self.logger.info('Updating personal standings')
        for person, mailing_lists in by_person.items():
            assert person.personal_standing == PersonalStanding.UNKNOWN, (
                'Expected UNKNOWN personal standing for %s, got %s' %
                (person.name, person.personal_standing))
            if len(mailing_lists) >= config.standingupdater.approvals_needed:
                self.logger.info('Setting standing for %s to GOOD',
                                 person.name)
                person.personal_standing = PersonalStanding.GOOD

        self.txn.commit()
        self.logger.info('Done.')
