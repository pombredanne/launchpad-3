# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Code import interfaces."""

__metaclass__ = type

__all__ = [
    'CodeImportReviewStatus',
    'ICodeImport',
    'ICodeImportSet',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Choice, Int, TextLine, Timedelta

from canonical.lazr import DBEnumeratedType, DBItem

from canonical.launchpad import _
from canonical.launchpad.fields import URIField
from canonical.launchpad.interfaces.productseries import (
    validate_cvs_module, validate_cvs_root, RevisionControlSystems)


class CodeImportReviewStatus(DBEnumeratedType):
    """CodeImport review status.

    Before a code import is performed, it is reviewed. Only reviewed imports
    are processed.
    """

    NEW = DBItem(1, """Pending Review

        This code import request has recently been filed an has not
        been reviewed yet.
        """)

    INVALID = DBItem(10, """Invalid

        This code import will not be processed.
        """)

    REVIEWED = DBItem(20, """Reviewed

        This code import has been approved and will be processed.
        """)

    SUSPENDED = DBItem(30, """Suspended

        This code import has been approved, but it has been suspended
        and is not processed.""")


class ICodeImport(Interface):
    """A code import to a Bazaar Branch."""

    id = Int(readonly=True, required=True)
    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)

    # XXX DavidAllouche 2007-07-04:
    # Branch should really be readonly, but there is a corner case of the
    # code-import-sync script where we have a need to change it. The readonly
    # parameter should be set back to True after the transition to the new
    # code import system is complete.
    branch = Choice(
        title=_('Branch'), required=True, readonly=False, vocabulary='Branch',
        description=_("The Bazaar branch produced by the import system."))

    registrant = Choice(
        title=_('Registrant'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam',
        description=_("The person who initially requested this import."))

    owner = Choice(
        title=_('Owner'), required=True, readonly=False,
        vocabulary='ValidPersonOrTeam',
        description=_("The community contact for this import."))

    assignee = Choice(
        title=_('Assignee'), required=False, readonly=False,
        vocabulary='ValidPersonOrTeam',
        description=_("The person in charge of handling this import."))

    product = Choice(
        title=_("Project"), required=True,
        readonly=True, vocabulary='Product',
        description=_("The project this code import belongs to."))

    series = Choice(
        title=_("Series"),
        readonly=True, vocabulary='ProductSeries',
        description=_("The series this import is registered as the "
                      "code for, or None if there is no such series."))

    review_status = Choice(
        title=_("Review Status"), vocabulary=CodeImportReviewStatus,
        default=CodeImportReviewStatus.NEW,
        description=_("Before a code import is performed, it is reviewed."
            " Only reviewed imports are processed."))

    rcs_type = Choice(title=_("Type of RCS"),
        required=True, vocabulary=RevisionControlSystems,
        description=_("The revision control system used by the import source. "
        "Can be CVS or Subversion."))

    svn_branch_url = URIField(title=_("Branch"), required=False,
        description=_("The URL of a Subversion branch, starting with svn:// or"
            " http(s)://. Only trunk branches are imported."),
        allowed_schemes=["http", "https", "svn"],
        allow_userinfo=False, # Only anonymous access is supported.
        allow_port=True,
        allow_query=False,    # Query makes no sense in Subversion.
        allow_fragment=False, # Fragment makes no sense in Subversion.
        trailing_slash=False) # See http://launchpad.net/bugs/56357.

    cvs_root = TextLine(title=_("Repository"), required=False,
        constraint=validate_cvs_root,
        description=_("The CVSROOT. "
            "Example: :pserver:anonymous@anoncvs.gnome.org:/cvs/gnome"))

    cvs_module = TextLine(title=_("Module"), required=False,
        constraint=validate_cvs_module,
        description=_("The path to import within the repository."
            " Usually, it is the name of the project."))

    date_last_successful = Datetime(title=_("Last successful"), required=False)

    update_interval = Timedelta(
        title=_("Update interval"), required=False, description=_(
        "The user-specified time between automatic updates of this import. "
        "If this is unspecified, the effective update interval is a default "
        "value selected by Launchpad administrators."))

    effective_update_interval = Timedelta(
        title=_("Effective update interval"), required=True, readonly=True,
        description=_(
        "The effective time between automatic updates of this import. "
        "If the user did not specify an update interval, this is a default "
        "value selected by Launchpad adminstrators."))


class ICodeImportSet(Interface):
    """Interface representing the set of code imports."""

    def new(registrant, branch, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """Create a new CodeImport."""

    # XXX DavidAllouche 2007-07-05:
    # newWithId is only needed for code-import-sync-script. This method
    # should be removed after the transition to the new code import system is
    # complete.

    def newWithId(id, registrant, branch, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """Create a new CodeImport with a specified database id."""

    def getAll():
        """Return an iterable of all CodeImport objects."""

    def get(id):
        """Get a CodeImport by its id.

        Raises `NotFoundError` if no such import exists.
        """

    def getByBranch(branch):
        """Get the CodeImport, if any, associated to a Branch."""

    def delete(id):
        """Delete a CodeImport given its id."""

    def search(review_status):
        """Find the CodeImports of the given status.

        :param review_status: An entry from the `CodeImportReviewStatus`
                              schema.
        """
