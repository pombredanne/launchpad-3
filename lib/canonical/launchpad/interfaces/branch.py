# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Branch interfaces."""

__metaclass__ = type

__all__ = [
    'IBranch',
    ]

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Interface, Attribute

from zope.schema import Choice, TextLine

from canonical.launchpad.fields import Summary, Title, TimeInterval
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad.interfaces.validation import valid_webref


_ = MessageIDFactory('launchpad')


class IBranch(IHasOwner):
    """A Bazaar branch."""

    name = TextLine(
        title=_('Name'), required=True, description=_("Keep this name very "
        "short, unique, and descriptive, because it will be used in URLs. "
        "Examples: mozilla-type-ahead-find, postgres-smart-serial."),
        constraint=valid_name)
    title = Title(
        title=_('Title'), required=True, description=_("Describe the "
        "branch as clearly as possible in up to 70 characters. This "
        "title is displayed in every branch list or report."))
    summary = Summary(
        title=_('Summary'), required=True, description=_("A "
        "single-paragraph description of the branch. This will also be "
        "displayed in most branch listings."))
    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    url = TextLine(
        title=_('Branch URL'), required=True,
        description=_('The URL of the branch. This is usually the URL used to'
                      ' checkout the branch.'), constraint=valid_webref)

    # product
    # registrant
    # branch_product_name
    # product_locked
    # home_page
    # branch_home_page

    # starred
    # whiteboard
    # branch_status
    # landing_target
    # current_delta_url
    # current_conflicts_url
    # current_diff_adds
    # current_diff_deletes
    # stats_updated
    # current_activity
    # mirror_status
    # last_mirrored
    # last_mirror_attempt
    # mirror_failures
    # cache_url

    # # joins
    # revisions
