# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for package-specific builds."""
__metaclass__ = type
__all__ = ['IPackageBuild']


from zope.interface import Interface, Attribute
from zope.schema import Choice, Object, TextLine
from lazr.restful.fields import Reference

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archive import IArchive


class IPackageBuild(Interface):
    """Attributes and operations specific to package build jobs."""

    id = Attribute("The package build ID.")

    archive = Reference(
            title=_("Archive"), schema=IArchive,
            required=True, readonly=True,
            description=_("The Archive context for this build."))

    pocket = Choice(
            title=_('Pocket'), required=True,
            vocabulary=PackagePublishingPocket,
            description=_("The build targeted pocket."))

    upload_log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_("The LibraryFileAlias containing the upload log for "
                "build resulting in an upload that could not be processed "
                "successfully. Otherwise it will be None."))

    dependencies = TextLine(
            title=_("Dependencies"), required=False,
            description=_("Debian-like dependency line that must be satisfied"
                          " before attempting to build this request."))
