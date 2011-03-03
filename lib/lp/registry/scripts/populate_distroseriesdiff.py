# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Populate `DistroSeriesDifference` table."""

__metaclass__ = type
__all__ = []

from storm.info import ClassAlias

from canonical.database.sqlbase import (
    quote,
    quote_identifier,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.distroseries import DistroSeries
from lp.soyuz.interfaces.publishing import active_publishing_status


def compose_sql_find_latest_source_package_releases(distroseries):
    parameters = {
        'active_status': quote(active_publishing_status),
        'distroseries': quote(distroseries),
        'main_archive': quote(distroseries.distribution.main_archive),
        'release_pocket': quote(PackagePublishingPocket.RELEASE)
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
    parameters = {
        'derived_query': compose_sql_find_latest_source_package_releases(
            derived_distroseries),
        'parent_query': compose_sql_find_latest_source_package_releases(
            derived_distroseries.parent_series),
    }
    return """
        SELECT DISTINCT
            COALESCE(parent.sourcepackagename, derived.sourcepackagename),
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
        WHERE (derived_series, source_package_name) NOT IN (
            SELECT derived_series, source_package_name
            FROM DistroSeriesDifference)
        """ % parameters


def drop_table(store, table):
    store.execute("DROP TABLE IF EXISTS %s" % quote_identifier(table))


def populate_distroseriesdiff(derived_distroseries):
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
    Parent = ClassAlias(DistroSeries, "Parent")
    return IStore(DistroSeries).find(
        DistroSeries,
        Parent.id == DistroSeries.parent_seriesID,
        Parent.distributionID != DistroSeries.distributionID)
