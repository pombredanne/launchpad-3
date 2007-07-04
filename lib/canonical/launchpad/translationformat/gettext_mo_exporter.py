# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'GettextMoExporter'
    ]

import os.path
import subprocess
from StringIO import StringIO
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationExporter,
    ITranslationFormatExporter, UnknownTranslationExporterError)
from canonical.launchpad.translationformat.translation_export import (
    LaunchpadWriteTarFile, ExportedTranslationFile)
from canonical.lp.dbschema import TranslationFileFormat

class MoCompiler:
    """Compile PO files to MO files."""

    MSGFMT = '/usr/bin/msgfmt'

    def compile(self, gettext_po_file):
        """Return a MO version of the given PO file."""

        msgfmt = subprocess.Popen(
            args=[MoCompiler.MSGFMT, '-v', '-o', '-', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        stdout, stderr = msgfmt.communicate(gettext_po_file)

        if msgfmt.returncode != 0:
            raise UnknownTranslationExporterError(
                "Got an error while compiling PO file into MO:\n%s" % stdout)

        return stdout


class GettextMoExporter:
    """Support class to export Gettext .mo files."""
    implements(ITranslationFormatExporter)

    def __init__(self, context):
        pass

    @property
    def format(self):
        """See `ITranslationFormatExporter`."""
        return TranslationFileFormat.MO

    @property
    def handlable_formats(self):
        """See `ITranslationFormatExporter`."""
        return [TranslationFileFormat.PO]

    def exportTranslationFiles(self, translation_file_list):
        """See `ITranslationFormatExporter`."""
        assert len(translation_file_list) > 0, (
            'Got an empty list of files to export!')

        translation_exporter = getUtility(ITranslationExporter)
        gettext_po_exporter = (
            translation_exporter.getTranslationFormatExporterByFileFormat(
                TranslationFileFormat.PO))
        exported_files = {}
        for translation_file in translation_file_list:
            # To generate MO files we need first its PO version and then,
            # generate the MO one.
            template_exported = gettext_po_exporter.exportTranslationFiles(
                [translation_file])
            if translation_file.is_template:
                # This exporter is not able to handle template files. In that
                # case, we leave it as .po file. For this file format exported
                # templates are stored in templates/ directory.
                file_path = 'templates/%s' % os.path.basename(
                    template_exported.path)
                exported_file_content = template_exported.content
                content_type = template_exported.content_type
            else:
                # Standard layout for MO files is
                # 'LANG_CODE/LC_MESSAGES/TRANSLATION_DOMAIN.mo'
                file_path = os.path.join(
                    translation_file_list.language_code,
                    'LC_MESSAGES',
                    '%s.mo' % translation_file_list.translation_domain)
                mo_compiler = MoCompiler()
                mo_content = mo_compiler.compile(exported_file_content)
                exported_file_content = mo_content
                content_type = 'application/x-gmo'

            exported_files[file_path] = exported_file_content

        exported_file = ExportedTranslationFile()
        if len(exported_files) == 1:
            # It's a single file export. Return it directly.
            exported_file.path = file_path
            exported_file.content = StringIO(exported_file_content)
            exported_file.content_type = content_type
        else:
            # There are multiple files being exported. We need to generate an
            # archive that include all them.
            exported_file.content = LaunchpadWriteTarFile.files_to_stream(
                exported_files)
            exported_file.content_type = 'application/x-gtar'
            # We cannot give a proper file path for the tarball, that's why we
            # don't set it. We leave that decision to the caller.

        return exported_file
