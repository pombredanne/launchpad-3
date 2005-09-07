# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Branch interfaces."""

__metaclass__ = type

__all__ = [
    'IBranch',
    ]

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Interface, Attribute

from zope.schema import Bool, Choice, Text, TextLine

from canonical.lp.dbschema import BranchLifecycleStatus

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
    title = TextLine(
        title=_('Title'), required=True, description=_("Describe the "
        "branch as clearly as possible in up to 70 characters. This "
        "title is displayed in every branch list or report."))
    summary = Text(
        title=_('Summary'), required=True, description=_("A "
        "single-paragraph description of the branch. This will also be "
        "displayed in most branch listings."))
    url = TextLine(
        title=_('Branch URL'), required=True,
        description=_("The URL of the branch. This is usually the URL used to"
                      " checkout the branch."), constraint=valid_webref)
    whiteboard = Text(title=_('Status Whiteboard'), required=False,
        description=_('Any notes on the status of this branch you would '
        'like to make. This field is a general whiteboard, your changes '
        'will override the previous version.'))

    # People attributes
    owner = Choice(
        title=_('Owner'), required=True, vocabulary='ValidPersonOrTeam')
    registrant = Choice(
        title=_('Registrant'), required=False, vocabulary='ValidPersonOrTeam')

    # Product attributes
    product = Choice(
        title=_('Product'), required=True, vocabulary='Product',
        description=_("The product to which this branch belongs."))
    product_name = Attribute("The name of the product, or '+junk'.")
    branch_product_name = Attribute(
        "The product name specified within the branch.")
    product_locked = Bool(
        title=_("Product Locked"),
        description=_("Whether the product name specified within the branch "
                      " is overriden by the product name set in Launchpad."))

    # Home page attributes
    home_page = TextLine(
        title=_('Home Page URL'), required=True,
        description=_("The URL of the branch home page, describing the "
                      "purpose of the branch."), constraint=valid_webref)
    branch_home_page = Attribute(
        "The home page URL specified within the branch.")
    home_page_locked = Bool(
        title=_("Home Page Locked"),
        description=_("Whether the home page specified within the branch "
                      " is overriden by the home page set in Launchpad."))

    # Stats and status attributes
    starred = Attribute("How many stars this branch has.")

    lifecycle_status = Choice(
        title=_('Status'), vocabulary='BranchLifecycleStatus',
        default=BranchLifecycleStatus.NEW, description=_("The current "
        "status of this branch."))

    # TODO: landing_target, needs a BranchVocabulaty
    # -- DavidAllouche 2005-09-05

    current_delta_url = Attribute(
        "URL of a page showing the delta produced "
        "by merging this branch into the landing branch.")
    current_diff_adds = Attribute(
        "Count of lines added in merge delta.")
    current_diff_deletes = Attribute(
        "Count of lines deleted in the merge delta.")
    current_conflicts_url = Attribute(
        "URL of a pag showing the conflicts produced "
        "by merging this branch into the landing branch.")
    current_activity = Attribute("Current branch activity.")
    stats_updated = Attribute("Last time the branch stats were updated.")

    # Mirroring attributes

    # TODO: mirror_status, needs a MirrorStatus EnumCol
    # -- DavidAllouche 2005-09-05

    last_mirrored = Attribute(
        "Last time this branch was successfully mirrored.")
    last_mirror_attempt = Attribute(
        "Last time a mirror of this branch was attempted.")
    mirror_failures = Attribute(
        "Number of failed mirror attempts since the last successful mirror.")

    cache_url = Attribute("Private mirror of the branch, for internal use.")

    # Joins
    revisions = Attribute("The sequence of revisions in that branch.")
    revision_count = Attribute("The number of revisions in that branch.")

    def latest_revisions(quantity=10):
        """A specific number of the latest revisions in that branch."""
