#!/usr/bin/python2.4
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Script to export a tarball of translations for a distro release."""

__metaclass__ = type

import _pythonpath

from canonical.launchpad.scripts.base import (LaunchpadScript,
    LaunchpadScriptFailure)
from canonical.launchpad.scripts.language_pack import export_language_pack


class RosettaLangPackExporter(LaunchpadScript):
    usage = '%prog [options] distribution release'
    def add_my_options(self):
        self.parser.add_option(
            '--email',
            dest='email_addresses',
            default=[],
            action='append',
            help='An email address to send a notification to.'
            )
        self.parser.add_option(
            '--output',
            dest='output',
            default=None,
            action='store',
            help='A file to send the generated tarball to, rather than the'
                 ' Libraran.'
            )
        self.parser.add_option(
            '--update',
            dest='update',
            default=False,
            action='store_true',
            help='Whether the generated language pack should be an update from'
                 ' the previous export.'
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
                'and release name')

        distribution_name, release_name = self.args
        self.logger.info(
            'Exporting translations for release %s of distribution %s',
            distribution_name, release_name)

        success = export_language_pack(
            distribution_name=distribution_name,
            release_name=release_name,
            component=self.options.component,
            update=self.options.update,
            force_utf8=self.options.force_utf8,
            output_file=self.options.output,
            email_addresses=self.options.email_addresses,
            logger=self.logger)

        if not success:
            raise LaunchpadScriptFailure('Language pack generation failed')

if __name__ == '__main__':
    script = RosettaLangPackExporter('rosetta-language-pack-export')
    script.lock_and_run()

