# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ArchiveDependencies model."""

__metaclass__ = type

__all__ = [
    'component_dependencies',
    'get_components_for_building',
    'get_primary_current_component',
    'get_sources_list_for_building',
    'pocket_dependencies',
    ]


from canonical.launchpad.interfaces.archive import ArchivePurpose
from canonical.launchpad.interfaces.publishing import (
    PackagePublishingPocket, PackagePublishingStatus, pocketsuffix)
from canonical.launchpad.webapp.uri import URI


component_dependencies = {
    'main': ['main'],
    'restricted': ['main', 'restricted'],
    'universe': ['main', 'universe'],
    'multiverse': ['main', 'restricted', 'universe', 'multiverse'],
    'partner' : ['partner'],
    }

pocket_dependencies = {
    PackagePublishingPocket.RELEASE: (
        PackagePublishingPocket.RELEASE,
        ),
    PackagePublishingPocket.SECURITY: (
        PackagePublishingPocket.RELEASE,
        PackagePublishingPocket.SECURITY,
        ),
    PackagePublishingPocket.UPDATES: (
        PackagePublishingPocket.RELEASE,
        PackagePublishingPocket.SECURITY,
        PackagePublishingPocket.UPDATES,
        ),
    PackagePublishingPocket.BACKPORTS: (
        PackagePublishingPocket.RELEASE,
        PackagePublishingPocket.SECURITY,
        PackagePublishingPocket.UPDATES,
        PackagePublishingPocket.BACKPORTS,
        ),
    PackagePublishingPocket.PROPOSED: (
        PackagePublishingPocket.RELEASE,
        PackagePublishingPocket.SECURITY,
        PackagePublishingPocket.UPDATES,
        PackagePublishingPocket.PROPOSED,
        ),
    }


def get_components_for_building(build):
    """Return the components allowed to be used in the build context.

    :param build: a context `IBuild`.
    :return: a list of component names.
    """
    # BACKPORTS should be able to fetch build dependencies from any
    # component in order to cope with component changes occurring
    # accross distroseries. See bug #198936 for further information.
    if build.pocket == PackagePublishingPocket.BACKPORTS:
        return component_dependencies['multiverse']

    return component_dependencies[build.current_component.name]


def get_sources_list_for_building(build):
    """Return the sources_list entries required to build the given item.

    :param build: a context `IBuild`.
    :return: a deb sources_list entries (lines).
    """
    ogre_components = get_components_for_building(build)

    deps = []

    if (build.archive.purpose == ArchivePurpose.PARTNER or
        build.archive.purpose == ArchivePurpose.PPA):
        # Although partner and PPA builds are always in the release
        # pocket, they depend on the same pockets as though they
        # were in the updates pocket.
        #
        # XXX Julian 2008-03-20
        # Private PPAs, however, behave as though they are in the
        # security pocket.  This is a hack to get the security
        # PPA working as required until cprov lands his changes for
        # configurable PPA pocket dependencies.
        if build.archive.private:
            primary_pockets = pocket_dependencies[
                PackagePublishingPocket.SECURITY]
            primary_components = component_dependencies[
                get_primary_current_component(build)]
        else:
            primary_pockets = pocket_dependencies[
                PackagePublishingPocket.UPDATES]
            primary_components = component_dependencies['multiverse']

        deps.append(
            (build.archive, PackagePublishingPocket.RELEASE,
             ogre_components)
            )

        for archive_dependency in build.archive.dependencies:
            deps.append(
                (archive_dependency.dependency,
                archive_dependency.pocket,
                ogre_components)
                )
    else:
        primary_pockets = pocket_dependencies[build.pocket]
        primary_components = ogre_components

    for pocket in primary_pockets:
        deps.append(
            (build.distribution.main_archive, pocket, primary_components)
            )

    return _get_sources_list_for_dependencies(deps, build.distroarchseries)


def get_primary_current_component(build):
    """Return the component name of the primary archive ancestry.

    If no ancestry could be found, default to 'universe'.
    """
    primary_archive = build.archive.distribution.main_archive
    ancestries = primary_archive.getPublishedSources(
        name=build.sourcepackagerelease.name,
        distroseries=build.distroseries, exact_match=True)

    # XXX cprov 20080923 bug=246200: This count should be replaced
    # by bool() (__non_zero__) when storm implementation gets fixed.
    if ancestries.count() > 0:
        return ancestries[0].component.name

    return 'universe'


def _has_published_binaries(archive, distroarchseries, pocket):
    """Whether or not the archive dependency has published binaries."""
    # The primary archive dependencies are always relevant.
    if archive.purpose == ArchivePurpose.PRIMARY:
        return True

    published_binaries = archive.getAllPublishedBinaries(
        distroarchseries=distroarchseries,
        status=PackagePublishingStatus.PUBLISHED)
    # XXX cprov 20080923 bug=246200: This count should be replaced
    # by bool() (__non_zero__) when storm implementation gets fixed.
    return published_binaries.count() > 0


def _get_binary_sources_list_line(archive, distroarchseries, pocket,
                                  components):
    """Return the correponding binary sources_list line."""
    # Encode the private PPA repository password in the
    # sources_list line. Note that the buildlog will be
    # sanitized to not expose it.
    if archive.private:
        uri = URI(archive.archive_url)
        uri = uri.replace(
            userinfo="buildd:%s" % archive.buildd_secret)
        url = str(uri)
    else:
        url = archive.archive_url

    suite = distroarchseries.distroseries.name + pocketsuffix[pocket]
    return 'deb %s %s %s' % (url, suite, ' '.join(components))


def _get_sources_list_for_dependencies(dependencies, distroarchseries):
    """ """
    sources_list_lines = []
    for archive, pocket, components in dependencies:
        has_published_binaries = _has_published_binaries(
            archive, distroarchseries, pocket)
        if not has_published_binaries:
            continue
        sources_list_line = _get_binary_sources_list_line(
            archive, distroarchseries, pocket, components)
        sources_list_lines.append(sources_list_line)

    return sources_list_lines

