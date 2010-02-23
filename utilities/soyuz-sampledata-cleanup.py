#!/usr/bin/python2.5
# pylint: disable-msg=W0403

"""Clean up sample data so it will allow Soyuz to run locally.

DO NOT RUN ON PRODUCTION SYSTEMS.  This script deletes lots of
Ubuntu-related data.
"""

__metaclass__ = type

__all__ = ['main']


import _pythonpath

from optparse import OptionParser
from os import getenv
import re
import sys

from zope.component import getUtility
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from zope.security.proxy import removeSecurityProxy

from storm.store import Store

from canonical.database.sqlbase import sqlvalues

from canonical.lp import initZopeless

from canonical.launchpad.interfaces.launchpad import (
    ILaunchpadCelebrities)
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.scripts.logger import logger, logger_options
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, SLAVE_FLAVOR)

from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.section import ISectionSet
from lp.soyuz.model.section import SectionSelection
from lp.soyuz.model.component import ComponentSelection


class DoNotRunOnProduction(Exception):
    """Error: do not run this script on production (-like) systems."""


def get_max_id(store, table_name):
    """Find highest assigned id in given table."""
    max_id = store.execute("SELECT max(id) FROM %s" % table_name).get_one()
    if max_id is None:
        return None
    else:
        return max_id[0]


def check_preconditions(options):
    """Try to ensure it's safe to run.

    This script must not run on a production server, or anything
    remotely like it.
    """
    store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)

    # Just a guess, but dev systems aren't likely to have ids this high
    # in this table.  Production data does.
    real_data = (get_max_id(store, "TranslationMessage") >= 1000000)
    if real_data and not options.force:
        raise DoNotRunOnProduction(
            "Refusing to delete Ubuntu data unless you --force me.")

    # For some configs it's just absolutely clear this script shouldn't
    # run.  Don't even accept --force there.
    forbidden_configs = re.compile('(edge|lpnet|production)')
    current_config = getenv('LPCONFIG', 'an unknown config')
    if forbidden_configs.match(current_config):
        raise DoNotRunOnProduction(
            "I won't delete Ubuntu data on %s and you can't --force me."
            % current_config)


def parse_args(arguments):
    """Parse command-line arguments.

    :return: (options, args, logger)
    """
    parser = OptionParser(
        description="Delete existing Ubuntu releases and set up new ones.")
    parser.add_option('-f', '--force', action='store_true', dest='force',
        help="DANGEROUS: run even if the database looks production-like.")
    parser.add_option('-n', '--dry-run', action='store_true', dest='dry_run',
        help="Do not commit changes.")
    logger_options(parser)

    options, args = parser.parse_args(arguments)
    return options, args, logger(options)


def get_person(name):
    """Return `IPersonSet` utility."""
    # Avoid circular import.
    from lp.registry.interfaces.person import IPersonSet
    return getUtility(IPersonSet).getByName(name)


def retire_series(distribution):
    """Mark all `DistroSeries` for `distribution` as obsolete."""
    for series in distribution.series:
        series.status = SeriesStatus.OBSOLETE


def retire_active_publishing_histories(histories, requester):
    """Retire all active publishing histories in the given collection."""
    # Avoid circular import.
    from lp.soyuz.interfaces.publishing import active_publishing_status
    for history in histories(status=active_publishing_status):
        history.requestDeletion(
            requester, "Cleaned up because of missing Librarian files.")


def retire_distro_archives(distribution, culprit):
    """Retire all items in `distribution`'s archives."""
    for archive in distribution.all_distro_archives:
        retire_active_publishing_histories(
            archive.getPublishedSources, culprit)
        retire_active_publishing_histories(
            archive.getAllPublishedBinaries, culprit)


def retire_ppas(distribution):
    """Disable all PPAs for `distribution`."""
    for ppa in distribution.getAllPPAs():
        removeSecurityProxy(ppa).publish = False


def set_lucille_config(distribution):
    """Set lucilleconfig on all series of `distribution`."""
    for series in distribution.series:
        removeSecurityProxy(series).lucilleconfig = '''[publishing]
components = main restricted universe multiverse'''


def create_sections(distroseries):
    """Set up some sections for `distroseries`."""
    section_names = (
        'admin', 'cli-mono', 'comm', 'database', 'devel', 'debug', 'doc',
        'editors', 'electronics', 'embedded', 'fonts', 'games', 'gnome',
        'graphics', 'gnu-r', 'gnustep', 'hamradio', 'haskell', 'httpd',
        'interpreters', 'java', 'kde', 'kernel', 'libs', 'libdevel', 'lisp',
        'localization', 'mail', 'math', 'misc', 'net', 'news', 'ocaml',
        'oldlibs', 'otherosfs', 'perl', 'php', 'python', 'ruby', 'science',
        'shells', 'sound', 'tex', 'text', 'utils', 'vcs', 'video', 'web',
        'x11', 'xfce', 'zope')
    store = Store.of(distroseries)
    for section_name in section_names:
        section = getUtility(ISectionSet).ensure(section_name)
        if section not in distroseries.sections:
            store.add(
                SectionSelection(distroseries=distroseries, section=section))


def create_components(distroseries, uploader):
    """Set up some components for `distroseries`."""
    component_names = ('main', 'restricted', 'universe', 'multiverse')
    store = Store.of(distroseries)
    main_archive = distroseries.distribution.main_archive
    for component_name in component_names:
        component = getUtility(IComponentSet).ensure(component_name)
        if component not in distroseries.components:
            store.add(
                ComponentSelection(
                    distroseries=distroseries, component=component))
        main_archive.newComponentUploader(uploader, component)
        main_archive.newQueueAdmin(uploader, component)


def create_series(parent, full_name, version, status):
    """Set up a `DistroSeries`."""
    distribution = parent.distribution
    owner = parent.owner
    name = full_name.split()[0].lower()
    title = "The " + full_name
    displayname = full_name.split()[0]
    new_series = distribution.newSeries(name=name, title=title,
        displayname=displayname, summary='Ubuntu %s is good.' % version,
        description='%s is awesome.' % version, version=version,
        parent_series=parent, owner=owner)
    new_series.status = status
    notify(ObjectCreatedEvent(new_series))

    # This bit copied from scripts/ftpmaster-tools/initialise-from-parent.py.
    assert new_series.architectures.count() == 0, (
        "Cannot copy distroarchseries from parent; this series already has "
        "distroarchseries.")

    store = Store.of(parent)
    store.execute("""
        INSERT INTO DistroArchSeries
          (distroseries, processorfamily, architecturetag, owner, official)
        SELECT %s, processorfamily, architecturetag, %s, official
        FROM DistroArchSeries WHERE distroseries = %s
        """ % sqlvalues(new_series, owner, parent))

    i386 = new_series.getDistroArchSeries('i386')
    i386.supports_virtualized = True
    new_series.nominatedarchindep = i386

    new_series.initialiseFromParent()
    return new_series


def create_sample_series(original_series, log):
    """Set up sample `DistroSeries`.

    :param original_series: The parent for the first new series to be
        created.  The second new series will have the first as a parent,
        and so on.
    """
    series_descriptions = [
        ('Dapper Drake', SeriesStatus.SUPPORTED, '6.06'),
        ('Edgy Eft', SeriesStatus.OBSOLETE, '6.10'),
        ('Feisty Fawn', SeriesStatus.OBSOLETE, '7.04'),
        ('Gutsy Gibbon', SeriesStatus.OBSOLETE, '7.10'),
        ('Hardy Heron', SeriesStatus.SUPPORTED, '8.04'),
        ('Intrepid Ibex', SeriesStatus.SUPPORTED, '8.10'),
        ('Jaunty Jackalope', SeriesStatus.SUPPORTED, '9.04'),
        ('Karmic Koala', SeriesStatus.CURRENT, '9.10'),
        ('Lucid Lynx', SeriesStatus.DEVELOPMENT, '10.04'),
        ]

    parent = original_series
    for full_name, status, version in series_descriptions:
        log.info('Creating %s...' % full_name)
        parent = create_series(parent, full_name, version, status)


def clean_up(distribution, log):
    # First we eliminate all active publishings in the Ubuntu main archives.
    # None of the librarian files exist, so it kills the publisher.

    # Could use IPublishingSet.requestDeletion() on the published sources to
    # get rid of the binaries too, but I don't trust that there aren't
    # published binaries without corresponding sources.

    log.info("Deleting all items in official archives...")
    retire_distro_archives(distribution, get_person('name16'))

    # Disable publishing of all PPAs, as they probably have broken
    # publishings too.
    log.info("Disabling all PPAs...")
    retire_ppas(distribution)

    retire_series(distribution)


def populate(distribution, parent_series_name, uploader_name, log):
    """Set up sample data on `distribution`."""
    parent_series = distribution.getSeries(parent_series_name)

    # Set up lucilleconfig on all series.  The sample data lacks this.
    log.info("Setting lucilleconfig...")
    set_lucille_config(distribution)

    log.info("Configuring sections...")
    create_sections(parent_series)

    log.info("Configuring components and permissions...")
    create_components(parent_series, get_person(uploader_name))

    create_sample_series(parent_series, log)


def main(argv):
    options, args, log = parse_args(argv[1:])

    execute_zcml_for_scripts()
    txn = initZopeless(dbuser='launchpad')

    check_preconditions(options.force)

    ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    clean_up(ubuntu, log)

    # Use Hoary as the root, as Breezy and Grumpy are broken.
    populate(ubuntu, 'hoary', 'ubuntu-team', log)

    if options.dry_run:
        txn.abort()
    else:
        txn.commit()


if __name__ == "__main__":
    main(sys.argv)
