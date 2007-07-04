# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'GettextMoExporter'
    ]

from canonical.launchpad.interfaces import ITranslationFormatExporter


class MoCompiler:
    """Compile PO files to MO files."""

    MSGFMT = '/usr/bin/msgfmt'

    def compile(self, gettext_po_file):
        """Return a MO version of the given PO file."""

        msgfmt = subprocess.Popen(
            args=[MOCompiler.MSGFMT, '-v', '-o', '-', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        stdout, stderr = msgfmt.communicate(gettext_po_file)

        if msgfmt.returncode != 0:
            raise MOCompilationError("PO file compilation failed:\n" + stdout)

        return stdout


class GettextMoExporter:
    """Support class to export Gettext .mo files."""

    @property
    def format(self):
        """See `ITranslationFormatExporter`."""
        return TranslationFileFormat.MO

    @property
    def content_type(self):
        """See `ITranslationFormatExporter`."""
        return 'application/x-po'

    @property
    def file_path(self):
        """See `ITranslationFormatExporter`."""
            return po_filename[:-3] + '.mo'


    def exportTranslationFiles(self, translation_file_list):
        """See `ITranslationFormatExporter`."""
        translation_exporter = getUtility(ITranslationExporter)
        gettext_po_exporter = (
            translation_exporter.getTranslationFormatExporterByFileFormat(
                TranslationFileFormat.PO))
        exported_files = {}
        for translation_file in translation_file_list:
            exported_file = gettext_po_exporter.exportTranslationFiles(
                [translation_file])
            if translation_file.is_template:
                # This exporter is not able to handle template files. In that
                # case, we leave it as .po file.
                file_path = exported_file.file_path
            else:
                mo_compiler = MOCompiler()
                mo_content = mo_compiler.compile(exported_file.read())
                exported_file = StringIO(mo_content)
                filename = '%s.mo' % (
                    self._pofile.potemplate.potemplatename.translationdomain)
                file_path = os.path.join(translation_file.path, filename)

            exported_files[file_path] = exported_file


class MOFormatHandler(Handler):
    """Export handler for MO format exports."""

    def get_filename(self):
        """Return a filename for the file being exported."""

        if is_potemplate(self.obj):
            return POFormatHandler(self.obj).get_filename()
        else:
            po_filename = POFormatHandler(self.obj).get_filename()
            return po_filename[:-3] + '.mo'
