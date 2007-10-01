#!/usr/bin/python2.4
# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Script to export a tarball of translations for a distro series."""

__metaclass__ = type

import _pythonpath

from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)
from canonical.launchpad.scripts.language_pack import export_language_pack


class RosettaLangPackExporter(LaunchpadCronScript):
    usage = '%prog [options] distribution series'

    def add_my_options(self):
        self.parser.add_option(
            '--output',
            dest='output',
            default=None,
            action='store',
            help='A file to send the generated tarball to, rather than the'
                 ' Libraran.'
            )
        self.parser.add_option(
            '--component',
            dest='component',
            default=None,
            action='store',
            help='Select a concrete archive component to export.'
            )
        self.parser.add_option(
            '--force-utf8-encoding',
            dest='force_utf8',
            default=False,
            action='store_true',
            help='Whether the exported files should be exported using UTF-8'
                 ' encoding.'
            )

    def main(self):
        if len(self.args) != 2:
            raise LaunchpadScriptFailure(
                'Wrong number of arguments: should include distribution '
                'and series name')

        distribution_name, series_name = self.args
        self.logger.info(
            'Exporting translations for series %s of distribution %s',
            distribution_name, series_name)

        success = export_language_pack(
            distribution_name=distribution_name,
            series_name=series_name,
            component=self.options.component,
            force_utf8=self.options.force_utf8,
            output_file=self.options.output,
            logger=self.logger)

        if not success:
            raise LaunchpadScriptFailure('Language pack generation failed')
        else:
            self.txn.commit()


if __name__ == '__main__':
    script = RosettaLangPackExporter('language-pack-exporter')
    script.lock_and_run()

