# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Code import interfaces."""

__metaclass__ = type

__all__ = ['ICodeImport', 'ICodeImportSet']

from zope.interface import Attribute, Interface
from zope.schema import DateTime, Choice, Int, TextLine

from canonical.launchpad.fields import URIField
from canonical.launchpad.interfaces.productseries import (
    validate_cvs_module, validate_cvs_root)
from canonical.launchpad.validators.name import name_validator

class ICodeImport(Interface):
    """A code import to a Bazaar Branch."""

    id = Int(readonly=True, required=True)
    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    name = TextLine(
        title=_('Name'), required=True, 
        description=_("Unique name of the import used in the URL."),
        constraint=name_validator)
    product = Choice(
        title=_('Project'), required=True, vocabulary='Product',
        description=_("The project this code import belongs to."))
    series = Attribute("The release series whose branch will be set to the "
        "imported branch when it is first published.")
    branch = Attribute('The Bazaar branch produced by the import system.')

    rcs_type = Choice(title=_("Type of RCS"),
        required=True, vocabulary='RevisionControlSystems',
        description=_("The revision control system used by the import source. "
        "Can be CVS or Subversion."))

    svn_branch_url = URIField(title=_("Branch"), required=False,
        description=_("The URL of a Subversion branch, starting with svn:// or"
            " http(s)://. Only trunk branches are imported."),
        allowed_schemes=["http", "https", "svn", "svn+ssh"],
        allow_userinfo=False, # Only anonymous access is supported.
        allow_port=True,
        allow_query=False,    # Query makes no sense in Subversion.
        allow_fragment=False, # Fragment makes no sense in Subversion.
        trailing_slash=False) # See http://launchpad.net/bugs/56357.

    cvs_root = TextLine(title=_("Repository"), required=False,
        constraint=validate_cvs_root,
        description=_('The CVSROOT. '
            'Example: :pserver:anonymous@anoncvs.gnome.org:/cvs/gnome'))
    cvs_module = TextLine(title=_("Module"), required=False,
        constraint=validate_cvs_module,
        description=_('The path to import within the repository.'
            ' Usually, it is the name of the project.'))


class ICodeImportSet(Interface):
    """Interface representing the set of code imports."""

    def new(name, product, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """Create a new CodeImport."""
