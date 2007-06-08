# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface

__metaclass__ = type

__all__ = ('IPOFileOutput', 'IPOTemplateExporter', 'IDistroSeriesPOExporter',
           'IPOExport')

class IPOFileOutput(Interface):
    """Accept PO files for output.

    PO files are sent for output using the __call__ method.
    """

    def __call__(potemplate, language, variant, contents):
        """Accept a PO file for output.

        Where the PO file will be output to is implementation-specific.
        """

class IPOTemplateExporter(Interface):
    """Export PO files for a PO template."""

    def export_pofile(language, variant=None, include_obsolete=True,
        force_utf8=False):
        """Return the contents of the PO file as a string.

        :language: The language that we want to export.
        :variant: The variant for the given :language:.
        :include_obsolete: Whether the obsolete entries are not exported.
        :force_utf8: Whether the exported string should be encoded as UTF-8.
        """

    def export_pofile_to_file(filehandle, language, variant=None,
                              included_obsolete=True, force_utf8=False):
        """Return the contents of the PO file to a file handle.

        :language: The language that we want to export.
        :variant: The variant for the given :language:.
        :include_obsolete: Whether the obsolete entries are not exported.
        :force_utf8: Whether the exported string should be encoded as UTF-8.
        """

    def export_potemplate():
        """Export a single PO template.

        Return the contents of the PO template as a string.
        """

    def export_potemplate_to_file(filehandle):
        """Export a single PO template to a file handle."""

    def export_tarball():
        """Export all translations in a tarball.

        Returns the contents of the tarball as a string.
        """

    def export_tarball_to_file(filehandle):
        """Export all translation in a tarball to a file handle."""


class IDistroSeriesPOExporter(Interface):
    """Export PO files in a distro series."""

    def export_tarball():
        """Export all translations in a tarball.

        Returns the contents of the tarball as a string.
        """

    def export_tarball_to_file(filehandle):
        """Export all translation in a tarball to a file handle."""


class IPOExport(Interface):
    """Interface to export .po/.pot files"""

    def export(language):
        """Exports the .po file for the specific language"""
