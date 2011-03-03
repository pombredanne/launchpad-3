# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Populate `DistroSeriesDifference` table.

This script creates `DistroSeriesDifference` entries for the package
version differences between a derived `DistroSeries` and its parent.

The entries will still need to be processed by the cron job that works
out the exact differences.  Any pre-existing `DistroSeriesDifference`
entries remain untouched.
"""

__metaclass__ = type
__all__ = [
    'PopulateDistroSeriesDiff',
    ]

from optparse import (
    Option,
    OptionValueError,
    )
from storm.info import ClassAlias
from zope.component import getUtility

from canonical.database.sqlbase import (
    quote,
    quote_identifier,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.distroseries import DistroSeries
from lp.services.scripts.base import LaunchpadScript
from lp.soyuz.interfaces.publishing import active_publishing_status


def compose_sql_find_latest_source_package_releases(distroseries):
    """Produce SQL that gets the last-published `SourcePackageRelease`s.

    Within `distroseries`, looks for the `SourcePackageRelease`
    belonging to each respective `SourcePackageName`'s respective latest
    `SourcePackagePublishingHistory`.

    For each of those, it produces a tuple consisting of:
     * `SourcePackageName` id: sourcepackagename
     * `SourcePackageRelease` id: sourcepackagerelease
     * Source package version: version.

    :return: SQL query, as a string.
    """
    parameters = {
        'active_status': quote(active_publishing_status),
        'distroseries': quote(distroseries),
        'main_archive': quote(distroseries.distribution.main_archive),
        'release_pocket': quote(PackagePublishingPocket.RELEASE),
    }
    return """
        SELECT DISTINCT ON (SPR.sourcepackagename)
            SPR.sourcepackagename,
            SPR.id As sourcepackagerelease,
            SPR.version
        FROM SourcePackagePublishingHistory AS SPPH
        JOIN SourcePackageRelease AS SPR ON SPR.id = SPPH.sourcepackagerelease
        WHERE
            SPPH.distroseries = %(distroseries)s AND
            SPPH.archive = %(main_archive)s AND
            SPPH.pocket = %(release_pocket)s AND
            SPPH.status IN %(active_status)s
        ORDER BY SPR.sourcepackagename, SPPH.id DESC
        """ % parameters


def compose_sql_find_differences(derived_distroseries):
    """Produce SQL that finds differences for a `DistroSeries`.

    The query compares `derived_distroseries` and its `parent_series`
    and for each package whose latest `SourcePackageRelease`s in the
    respective series differ, produces a tuple of:
     * `SourcePackageName` id: sourcepackagename
     * Source package version in derived series: source_version
     * Source package version in parent series: parent_source_version.

    :return: SQL query, as a string.
    """
    parameters = {
        'derived_query': compose_sql_find_latest_source_package_releases(
            derived_distroseries),
        'parent_query': compose_sql_find_latest_source_package_releases(
            derived_distroseries.parent_series),
    }
    return """
        SELECT DISTINCT
            COALESCE(
                parent.sourcepackagename,
                derived.sourcepackagename) AS sourcepackagename,
            derived.version AS source_version,
            parent.version AS parent_source_version
        FROM (%(parent_query)s) AS parent
        FULL OUTER JOIN (%(derived_query)s) AS derived
        ON derived.sourcepackagename = parent.sourcepackagename
        WHERE
            derived.sourcepackagerelease IS DISTINCT FROM
                parent.sourcepackagerelease
        """ % parameters


def compose_sql_difference_type():
    """Produce SQL to compute a difference's `DistroSeriesDifferenceType`.

    Works with the parent_source_version and source_version fields as
    produced by the SQL from `compose_sql_find_differences`.

    :return: SQL query, as a string.
    """
    parameters = {
        'unique_to_derived_series': quote(
            DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES),
        'missing_from_derived_series': quote(
            DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES),
        'different_versions': quote(
            DistroSeriesDifferenceType.DIFFERENT_VERSIONS),
    }
    return """
        CASE
            WHEN parent_source_version IS NULL THEN
                %(unique_to_derived_series)s
            WHEN source_version IS NULL THEN
                %(missing_from_derived_series)s
            ELSE %(different_versions)s
        END
        """ % parameters


def compose_sql_populate_distroseriesdiff(derived_distroseries, temp_table):
    """Create `DistroSeriesDifference` rows based on found differences.

    Uses field values that describe the difference, as produced by the
    SQL from `compose_sql_find_differences`:
     * sourcepackagename
     * source_version
     * parent_source_version

    Existing `DistroSeriesDifference` rows are not affected.

    :param derived_distroseries: A derived `DistroSeries`.
    :param temp_table: The name of a table to select the input fields
        from.
    :return: SQL query, as a string.
    """
    parameters = {
        'derived_series': quote(derived_distroseries),
        'difference_type_expression': compose_sql_difference_type(),
        'needs_attention': quote(
            DistroSeriesDifferenceStatus.NEEDS_ATTENTION),
        'temp_table': quote_identifier(temp_table),
    }
    return """
        INSERT INTO DistroSeriesDifference (
            derived_series,
            source_package_name,
            status,
            difference_type,
            source_version,
            parent_source_version)
        SELECT
            %(derived_series)s,
            sourcepackagename,
            %(needs_attention)s,
            %(difference_type_expression)s,
            source_version,
            parent_source_version
        FROM %(temp_table)s
        WHERE sourcepackagename NOT IN (
            SELECT source_package_name
            FROM DistroSeriesDifference
            WHERE derived_series = %(derived_series)s)
        """ % parameters


def drop_table(store, table):
    """Drop `table`, if it exists."""
    store.execute("DROP TABLE IF EXISTS %s" % quote_identifier(table))


def populate_distroseriesdiff(derived_distroseries):
    """Compare `derived_distroseries` to parent, and register differences.

    The differences are registered by creating `DistroSeriesDifference`
    records, insofar as they do not yet exist.
    """
    temp_table = "temp_potentialdistroseriesdiff"

    store = IStore(derived_distroseries)
    drop_table(store, temp_table)
    store.execute("CREATE TEMP TABLE %s AS %s" % (
        quote_identifier(temp_table),
        compose_sql_find_differences(derived_distroseries)))
    store.execute(
        compose_sql_populate_distroseriesdiff(
            derived_distroseries, temp_table))
    drop_table(store, temp_table)


def find_derived_series():
    """Find all derived `DistroSeries`.

    Derived `DistroSeries` are ones that have a `parent_series`, but
    where the `parent_series` is not in the same distribution.
    """
    Parent = ClassAlias(DistroSeries, "Parent")
    return IStore(DistroSeries).find(
        DistroSeries,
        Parent.id == DistroSeries.parent_seriesID,
        Parent.distributionID != DistroSeries.distributionID)


class PopulateDistroSeriesDiff(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_options([
            Option(
                '-a', '--all', dest='all', action='store_true', default=False,
                help="Populate all derived distribution series."),
            Option(
                '-d', '--distribution', dest='distribution', default=None,
                help="Derived distribution."),
            Option('-s', '--series', dest='series', default=None,
                help="Derived distribution series.")])

    def getDistroSeries(self):
        if self.options.all:
            return list(find_derived_series())
        else:
            distro = getUtility(IDistributionSet).getByName(
                self.options.distribution)
            return [distro.getSeries(self.options.series)]

    def main(self):
        specified_distro = (self.options.distribution is not None)
        specified_series = (self.options.series is not None)
        if specified_distro != specified_series:
            raise OptionValueError(
                "Specify neither a distribution or a series, or both.")
        if specified_distro == self.options.all:
            raise OptionValueError(
                "Either specify a distribution series, or use --all.")

        self.distroseries = self.getDistroSeries()
        for series in self.distroseries:
            self.logger.info("Looking for differences in %s.", series)
            populate_distroseriesdiff(series)
