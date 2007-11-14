#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

import _pythonpath
import sys
from optparse import OptionParser
from zope.component import getUtility
from canonical.config import config
from canonical.lp import initZopeless
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.scripts import logger, logger_options


def parse_options(args):
    """Parse a set of command line options.

    Return an optparse.Values object.
    """
    parser = OptionParser()
    parser.add_option("-d", "--distribution", dest="distro",
        default='ubuntu',
        help="The distribution we want to check.")
    parser.add_option("-r", "--release", dest="release",
        help="The distroseries that we want to check.")

    logger_options(parser)

    (options, args) = parser.parse_args(args)

    return options

def compare_translations(orig_distroseries, dest_distroseries):

    from difflib import unified_diff

    orig_templates = sorted(
        orig_distroseries.potemplates,
        key=lambda x: (x.potemplatename.name, x.sourcepackagename.name))
    dest_templates = sorted(
        dest_distroseries.potemplates,
        key=lambda x: (x.potemplatename.name, x.sourcepackagename.name))

    for i in range(len(orig_templates)):
        old_template = orig_templates[i]
        new_template = dest_templates[i]
        output = '\n'.join(list(unified_diff(
            old_template.export().split('\n'),
            new_template.export().split('\n'))))
        output = output.decode('UTF-8')
        if len(output) > 0:
            return u'%s is different than its parent %s:\n%s' % (
                new_template.title, old_template.title, output)
        for old_pofile in old_template.pofiles:
            new_pofile = new_template.getPOFileByLang(
                old_pofile.language.code, old_pofile.variant)
            old_pofile_content = old_pofile.uncachedExport(
                    included_obsolete=False,
                    force_utf8=True).split('\n')
            new_pofile_content = new_pofile.uncachedExport(
                    included_obsolete=False,
                    force_utf8=True).split('\n')
            output = '\n'.join(list(unified_diff(
                old_pofile_content, new_pofile_content)))
            output = output.decode('UTF-8')
            if len(output) > 0:
                return u'%s is different than its parent %s:\n%s' % (
                    new_pofile.title, old_pofile.title, output)
    return None

def main(argv):
    options = parse_options(argv[1:])

    logger_object = logger(options, 'check')

    # Setup zcml machinery to be able to use getUtility
    execute_zcml_for_scripts()
    ztm = initZopeless()

    distribution = getUtility(IDistributionSet)[options.distro]
    release = distribution[options.release]

    logger_object.info('Starting...')
    output = compare_translations(release.parent_series, release)
    if output is not None:
        logger_object.error(output)
    logger_object.info('Done...')


if __name__ == '__main__':
    main(sys.argv)
