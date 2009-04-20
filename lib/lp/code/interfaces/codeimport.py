# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Code import interfaces."""

__metaclass__ = type

__all__ = [
    'CodeImportReviewStatus',
    'ICodeImport',
    'ICodeImportSet',
    'RevisionControlSystems',
    ]

import re

from zope.interface import Attribute, Interface
from zope.schema import Datetime, Choice, Int, TextLine, Timedelta
from CVS.protocol import CVSRoot, CvsRootError
from lazr.enum import DBEnumeratedType, DBItem

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice, URIField
from canonical.launchpad.validators import LaunchpadValidationError


class RevisionControlSystems(DBEnumeratedType):
    """Revision Control Systems

    Bazaar brings code from a variety of upstream revision control
    systems into bzr. This schema documents the known and supported
    revision control systems.
    """

    CVS = DBItem(1, """
        Concurrent Versions System

        Imports from CVS via CSCVS.
        """)

    SVN = DBItem(2, """
        Subversion

        Imports from SVN using CSCVS.
        """)

    BZR_SVN = DBItem(3, """
        Subversion via bzr-svn

        Imports from SVN using bzr-svn.
        """)

    GIT = DBItem(4, """
        Git

        Imports from Git using bzr-git.
        """)


class CodeImportReviewStatus(DBEnumeratedType):
    """CodeImport review status.

    Before a code import is performed, it is reviewed. Only reviewed imports
    are processed.
    """

    NEW = DBItem(1, """Pending Review

        This code import request has recently been filed and has not
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

    FAILING = DBItem(40, """Failing

        The code import is failing for some reason and is no longer being
        attempted.""")


def validate_cvs_root(cvsroot):
    try:
        root = CVSRoot(cvsroot)
    except CvsRootError, e:
        raise LaunchpadValidationError(e)
    if root.method == 'local':
        raise LaunchpadValidationError('Local CVS roots are not allowed.')
    if root.hostname.count('.') == 0:
        raise LaunchpadValidationError(
            'Please use a fully qualified host name.')
    return True


def validate_cvs_module(cvsmodule):
    valid_module = re.compile('^[a-zA-Z][a-zA-Z0-9_/.+-]*$')
    if not valid_module.match(cvsmodule):
        raise LaunchpadValidationError(
            'The CVS module contains illegal characters.')
    if cvsmodule == 'CVS':
        raise LaunchpadValidationError(
            'A CVS module can not be called "CVS".')
    return True


def validate_cvs_branch(branch):
    if branch and re.match('^[a-zA-Z][a-zA-Z0-9_-]*$', branch):
        return True
    else:
        raise LaunchpadValidationError('Your CVS branch name is invalid.')


class ICodeImport(Interface):
    """A code import to a Bazaar Branch."""

    id = Int(readonly=True, required=True)
    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)

    branch = Choice(
        title=_('Branch'), required=True, readonly=True, vocabulary='Branch',
        description=_("The Bazaar branch produced by the import system."))

    registrant = PublicPersonChoice(
        title=_('Registrant'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam',
        description=_("The person who initially requested this import."))

    owner = PublicPersonChoice(
        title=_('Owner'), required=True, readonly=False,
        vocabulary='ValidPersonOrTeam',
        description=_("The community contact for this import."))

    assignee = PublicPersonChoice(
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
        description=_(
            "The version control system to import from. "
            "Can be CVS or Subversion."))

    svn_branch_url = URIField(title=_("Branch URL"), required=False,
        description=_(
            "The URL of a Subversion branch, starting with svn:// or"
            " http(s)://. Only trunk branches are imported."),
        allowed_schemes=["http", "https", "svn"],
        allow_userinfo=False, # Only anonymous access is supported.
        allow_port=True,
        allow_query=False,    # Query makes no sense in Subversion.
        allow_fragment=False, # Fragment makes no sense in Subversion.
        trailing_slash=False) # See http://launchpad.net/bugs/56357.

    git_repo_url = URIField(title=_("Repo URL"), required=False,
        description=_(
            "The URL of the git repository.  The MASTER branch will be "
            "imported."),
        allowed_schemes=["git"],
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

    date_last_successful = Datetime(
        title=_("Last successful"), required=False)

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
        "value selected by Launchpad administrators."))

    def getImportDetailsForDisplay():
        """Get a one-line summary of the location this import is from."""

    import_job = Choice(
        title=_("Current job"),
        readonly=True, vocabulary='CodeImportJob',
        description=_(
            "The current job for this import, either pending or running."))

    results = Attribute("The results for this code import.")

    def updateFromData(data, user):
        """Modify attributes of the `CodeImport`.

        Creates and returns a MODIFY `CodeImportEvent` if changes were made.

        This method preserves the invariant that a `CodeImportJob` exists for
        a given import if and only if its review_status is REVIEWED, creating
        and deleting jobs as necessary.

        :param data: dictionary whose keys are attribute names and values are
            attribute values.
        :param user: user who made the change, to record in the
            `CodeImportEvent`.
        :return: The MODIFY `CodeImportEvent`, if any changes were made, or
            None if no changes were made.
        """


class ICodeImportSet(Interface):
    """Interface representing the set of code imports."""

    def new(registrant, product, branch_name, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None, review_status=None):
        """Create a new CodeImport."""

    def getAll():
        """Return an iterable of all CodeImport objects."""

    def getActiveImports(text=None):
        """Return an iterable of all 'active' CodeImport objects.

        Active is defined, somewhat arbitrarily, as having
        review_status==REVIEWED and having completed at least once.

        :param text: If specifed, limit to the results to those that contain
            ``text`` in the product or project titles and descriptions.
        """

    def get(id):
        """Get a CodeImport by its id.

        Raises `NotFoundError` if no such import exists.
        """

    def getByBranch(branch):
        """Get the CodeImport, if any, associated to a Branch."""

    def getByCVSDetails(cvs_root, cvs_module):
        """Get the CodeImport with the specified CVS details."""

    def getByGitDetails(git_repo_url):
        """Get the CodeImport with the specified Git details."""

    def getBySVNDetails(svn_branch_url):
        """Get the CodeImport with the specified SVN details."""

    def delete(id):
        """Delete a CodeImport given its id."""

    def search(review_status):
        """Find the CodeImports of the given status.

        :param review_status: An entry from the `CodeImportReviewStatus`
                              schema.
        """
