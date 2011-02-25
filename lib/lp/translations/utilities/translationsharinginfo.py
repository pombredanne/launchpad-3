# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provide sharing information.

This module defines two different types of functions that provide
information about what sharing options are available on the other side of a
packaging link. Since they perform similar but slightly different complex
database queries combining them in any way will usually be wrong.

get_ubuntu_sharing_info and get_upstream_sharing_info will give you
information about the source package or productseries respectively,
combined with possibly available templates. You can restrict the search
by specifying a template name.

has_ubuntu_template and has_upstream_template make a direct search for a
template of the given name on the other side. They do not search for
source package or productseries but will only return True if an actual
template exists. That is a significant difference to the get_* functions.
"""

__metaclass__ = type
__all__ = [
    'get_ubuntu_sharing_info',
    'get_upstream_sharing_info',
    'has_ubuntu_template',
    'has_upstream_template',
    ]

from storm.expr import (\
    And,
    Join,
    LeftJoin,
    )

from canonical.launchpad.interfaces.lpstorm import IStore
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.packaging import Packaging
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.sourcepackage import SourcePackage
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.translations.model.potemplate import POTemplate


def find_ubuntu_sharing_info(productseries, templatename=None,
                             template_only=False):
    """Return a `ResultSet` of sharing information for this productseries.

    Target is either a productseries or a source package.
    :param productseries: The target productseries or None.
    :param templatename: The name of the template to find information for or
        None to get information about any sharing template in any series.
    :param template_only: Return only `POTemplate` instances.
    :returns: A result set of ('Distroseries', SourcePackageName, POTemplate)
        tuples.
    """

    # SELECT *
    # FROM Packaging
    # JOIN Distroseries
    #   ON Packaging.distroseries = Distroseries.id
    # JOIN SourcePackageName
    #   ON Packaging.sourcepackagename = SourcePackageName.id
    # LEFT JOIN POTemplate
    #   ON Packaging.distroseries = POTemplate.distroseries AND
    #      Packaging.sourcepackagename = POTemplate.sourcepackagename AND
    #      POTemplate.name = templatename
    # WHERE Packaging.productseries = productseries
    #
    if templatename is None:
        potemplate_condition = And(
            Packaging.distroseriesID == POTemplate.distroseriesID,
            Packaging.sourcepackagenameID == POTemplate.sourcepackagenameID)
    else:
        potemplate_condition = And(
            Packaging.distroseriesID == POTemplate.distroseriesID,
            Packaging.sourcepackagenameID ==
                POTemplate.sourcepackagenameID,
            POTemplate.name == templatename)
    if template_only:
        prejoin = Join(
            Packaging,
            POTemplate,
            potemplate_condition)
        result_classes = POTemplate
    else:
        prejoin = LeftJoin(
            Join(
                Join(
                    Packaging, DistroSeries,
                    Packaging.distroseriesID == DistroSeries.id),
                SourcePackageName,
                Packaging.sourcepackagenameID == SourcePackageName.id),
            POTemplate,
            potemplate_condition)
        result_classes = (DistroSeries, SourcePackageName, POTemplate)
    conditions = [
        Packaging.productseries == productseries,
        ]
    return IStore(Packaging).using(prejoin).find(
        result_classes, *conditions)


def find_upstream_sharing_info(sourcepackage,
                              templatename=None, template_only=False):
    """Return a `ResultSet` of sharing information for this sourcepackage.

    :param distroseries: The target distroseries or None.
    :param sourcepackagename: The target sourcepackagename or None.
    :param templatename: The name of the template to find information for or
        None to get information about any sharing template in any series.
    :param template_only: Return only `POTemplate` instances.
    :returns: A ResultSet of (ProductSeries, POTemplate) tuples.
    """
    # SELECT *
    # FROM Packaging
    # JOIN ProductSeries
    #   ON Packaging.productseries = Productseris.id
    # LEFT JOIN POTemplate
    #   ON Packaging.productseries = POTemplate.productseries AND
    #      POTemplate.name = templatename
    # WHERE Packaging.distroseries = distroseries AND
    #      Packaging.sourcepackagename = sourcepackagename
    #
    if templatename is None:
        potemplate_condition = (
            Packaging.productseriesID == POTemplate.productseriesID)
    else:
        potemplate_condition = And(
            Packaging.productseriesID == POTemplate.productseriesID,
            POTemplate.name == templatename)
    if template_only:
        prejoin = Join(
            Packaging, POTemplate, potemplate_condition)
        result_classes = POTemplate
    else:
        prejoin = LeftJoin(
            Join(
                Packaging, ProductSeries,
                Packaging.productseriesID == ProductSeries.id),
            POTemplate,
            potemplate_condition)
        result_classes = (ProductSeries, POTemplate)
    conditions = [
        Packaging.distroseries == sourcepackage.distroseries,
        Packaging.sourcepackagename == sourcepackage.sourcepackagename,
        ]

    return IStore(Packaging).using(prejoin).find(
        result_classes, *conditions)


def get_ubuntu_sharing_info(productseries, templatename=None):
    """Return a list of sharing information for the given target."""
    for result in find_ubuntu_sharing_info(productseries, templatename):
        distroseries, sourcepackagename, templatename = result
        yield (SourcePackage(sourcepackagename, distroseries), templatename)


def get_upstream_sharing_info(sourcepackage, templatename=None):
    """Return a list of sharing information for the given target."""
    return list(find_upstream_sharing_info(sourcepackage, templatename))


def has_ubuntu_template(productseries, templatename=None):
    """Check for existence of ubuntu template."""
    result = find_ubuntu_sharing_info(
        productseries, templatename, template_only=True)
    return not result.is_empty()


def has_upstream_template(sourcepackage, templatename=None):
    """Check for existence of upstream template."""
    result = find_upstream_sharing_info(
            sourcepackage, templatename, template_only=True)
    return not result.is_empty()
