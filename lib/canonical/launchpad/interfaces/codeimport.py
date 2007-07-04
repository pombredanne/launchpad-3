# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Code import interfaces."""

__metaclass__ = type

__all__ = [
    'ICodeImport',
    'ICodeImportSet',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Datetime, Choice, Int, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import URIField
from canonical.launchpad.interfaces.productseries import (
    validate_cvs_module, validate_cvs_root)
from canonical.launchpad.validators.name import name_validator
from canonical.lp.dbschema import CodeImportReviewStatus


class ICodeImport(Interface):
    """A code import to a Bazaar Branch."""

    id = Int(readonly=True, required=True)
    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)

    # XXX: branch should really be readonly, but there is a corner case of the
    # code-import-sync script where we have a need to change it. The readonly
    # parameter should be set back to True after the transition to the new code
    # import system is complete. -- DavidAllouche 2007-07-04.
    branch = Choice(
        title=_('Branch'), required=True, readonly=False, vocabulary='Branch',
        description=_("The Bazaar branch produced by the import system."))

    registrant = Choice(
        title=_('Registrant'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam',
        description=_("The Person who requested this import."))

    product = Choice(
        title=_("Project"), required=True,
        readonly=True, vocabulary='Product',
        description=_("The project this code import belongs to."))

    review_status = Choice(
        title=_("Review Status"), vocabulary='CodeImportReviewStatus',
        default=CodeImportReviewStatus.NEW,
        description=_("Before a code import is performed, it is reviewed."
            " Only reviewed imports are processed."))

    rcs_type = Choice(title=_("Type of RCS"),
        required=True, vocabulary='RevisionControlSystems',
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


class ICodeImportSet(Interface):
    """Interface representing the set of code imports."""

    def new(registrant, branch, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """Create a new CodeImport."""

    def newWithId(id, registrant, branch, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """Create a new CodeImport with a specified database id."""

    def getAll():
        """Return an iterable of all CodeImport objects."""

    def get(id):
        """Get a CodeImport by its id."""

    def getByBranch(branch):
        """Get the CodeImport, if any, associated to a Branch."""

    def delete(id):
        """Delete a CodeImport given its id."""
