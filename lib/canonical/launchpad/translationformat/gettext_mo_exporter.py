# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Export module for gettext's .mo file format."""

__metaclass__ = type

__all__ = [
    'GettextMOExporter',
    'POCompiler'
    ]

import os
import subprocess
from cStringIO import StringIO
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationExporter, ITranslationFormatExporter, TranslationFileFormat,
    UnknownTranslationExporterError)
from canonical.launchpad.translationformat.translation_export import (
    ExportedTranslationFile, LaunchpadWriteTarFile)


class POCompiler:
    """Compile PO files to MO files."""

    MSGFMT = '/usr/bin/msgfmt'

    def compile(self, gettext_po_file):
        """Return a MO version of the given PO file."""

        msgfmt = subprocess.Popen(
            args=[POCompiler.MSGFMT, '-v', '-o', '-', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = msgfmt.communicate(gettext_po_file)

        if msgfmt.returncode != 0:
            raise UnknownTranslationExporterError(
                'Error compiling PO file: %s\n%s' % (gettext_po_file, stderr))

        return stdout


class GettextMOExporter:
    """Support class to export Gettext .mo files."""
    implements(ITranslationFormatExporter)

    def __init__(self, context=None):
        # 'context' is ignored because it's only required by the way the
        # exporters are instantiated but it isn't used by this class.
        self.format = TranslationFileFormat.MO
        self.supported_source_formats = [TranslationFileFormat.PO]

    def exportTranslationMessageData(self, translation_message):
        """See `ITranslationFormatExporter`."""
        raise NotImplementedError(
            "This file format doesn't allow to export a single message.")

    def exportTranslationFiles(self, translation_file_list,
                               ignore_obsolete=False, force_utf8=False):
        """See `ITranslationFormatExporter`."""
        assert len(translation_file_list) > 0, (
            'Got an empty list of files to export!')

        translation_exporter = getUtility(ITranslationExporter)
        gettext_po_exporter = (
            translation_exporter.getExporterProducingTargetFileFormat(
                TranslationFileFormat.PO))
        exported_files = {}
        for translation_file in translation_file_list:
            # To generate MO files we need first its PO version and then,
            # generate the MO one.
            template_exported = gettext_po_exporter.exportTranslationFiles(
                [translation_file], ignore_obsolete, force_utf8)
            exported_file_content = template_exported.read()
            if translation_file.is_template:
                # This exporter is not able to handle template files. In that
                # case, we leave it as .po file. For this file format exported
                # templates are stored in templates/ directory.
                file_path = 'templates/%s' % os.path.basename(
                    template_exported.path)
                content_type = template_exported.content_type
                file_extension = template_exported.file_extension
            else:
                file_extension = 'mo'
                # Standard layout for MO files is
                # 'LANG_CODE/LC_MESSAGES/TRANSLATION_DOMAIN.mo'
                file_path = os.path.join(
                    translation_file.language_code,
                    'LC_MESSAGES',
                    '%s.%s' % (
                        translation_file.translation_domain,
                        file_extension))
                mo_compiler = POCompiler()
                mo_content = mo_compiler.compile(exported_file_content)
                exported_file_content = mo_content
                # We use x-gmo for consistency with other .po editors like
                # GTranslator.
                content_type = 'application/x-gmo'

            exported_files[file_path] = exported_file_content

        if len(exported_files) == 1:
            # It's a single file export. Return it directly.
            exported_file = ExportedTranslationFile(
                StringIO(exported_file_content))
            exported_file.path = file_path
            exported_file.content_type = content_type
            exported_file.file_extension = file_extension
        else:
            # There are multiple files being exported. We need to generate an
            # archive that include all them.
            exported_file = ExportedTranslationFile(
                LaunchpadWriteTarFile.files_to_stream(exported_files))
            # For tar.gz files, the standard content type is
            # application/x-gtar. You can see more info on
            # http://en.wikipedia.org/wiki/List_of_archive_formats
            exported_file.content_type = 'application/x-gtar'
            exported_file.file_extension = 'tar.gz'
            # By leaving path set to None, we let the caller decide.

        return exported_file
