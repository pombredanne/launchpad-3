# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Archive dependencies helper function.

This module contains the static maps representing the 'layered' component
and pocket dependencies and helper function to handler `ArchiveDependency`
records.

 * component_dependencies: static map of component dependencies
 * pocket_dependencies: static map of pocket dependencies

Auxiliary functions exposed for testing purposes:

 * get_components_for_building: return the corresponding component
       dependencies for a build, this result is known as 'ogre_components';
 * get_primary_current_component: return the component name where the
       building source is published in the primary archive.

`sources_list` content generation.

 * get_sources_list_for_building: return a list of `sources_list` lines
       that should be used to build the given `IBuild`.

"""

__metaclass__ = type

__all__ = [
    'component_dependencies',
    'default_component_dependency_name',
    'default_pocket_dependency',
    'get_components_for_building',
    'get_primary_current_component',
    'get_sources_list_for_building',
    'pocket_dependencies',
    ]


from lp.soyuz.interfaces.archive import (
    ArchivePurpose, ALLOW_RELEASE_BUILDS)
from lp.soyuz.interfaces.publishing import (
    PackagePublishingPocket, PackagePublishingStatus, pocketsuffix)
from lazr.uri import URI


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

default_pocket_dependency = PackagePublishingPocket.UPDATES

default_component_dependency_name = 'multiverse'


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


def get_sources_list_for_building(build):
    """Return the sources_list entries required to build the given item.

    :param build: a context `IBuild`.
    :return: a deb sources_list entries (lines).
    """
    deps = []

    # Consider primary archive dependency override. Add the default
    # primary archive dependencies if it's not present.
    if build.archive.getArchiveDependency(
        build.distribution.main_archive) is None:
        primary_dependencies = _get_default_primary_dependencies(build)
        deps.extend(primary_dependencies)

    # Consider user-selected archive dependencies.
    primary_component = get_primary_current_component(build)
    for archive_dependency in build.archive.dependencies:
        # When the dependency component is undefined, we should use
        # the component where the source is published in the primary
        # archive.
        if archive_dependency.component is None:
            components = component_dependencies[primary_component]
        else:
            components = component_dependencies[
                archive_dependency.component.name]
        # Follow pocket dependencies.
        for pocket in pocket_dependencies[archive_dependency.pocket]:
            deps.append(
                (archive_dependency.dependency, pocket, components)
                )

    # Add implicit self-dependency for non-primary contexts.
    if build.archive.purpose in ALLOW_RELEASE_BUILDS:
        deps.append(
            (build.archive, PackagePublishingPocket.RELEASE,
             get_components_for_building(build))
            )

    return _get_sources_list_for_dependencies(deps, build.distroarchseries)


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
    """Return a list of sources_list lines.

    Process the given list of dependency tuples for the given
    `DistroArchseries`.

    :param dependencies: list of 3 elements tuples as:
        (`IArchive`, `PackagePublishingPocket`, list of `IComponent` names)
    :param distroseries: target `IDistroSeries`;

    :return: a list of sources_list formatted lines.
    """
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


def _get_default_primary_dependencies(build):
    """Return the default primary dependencies for a given build.

    :param build: the `IBuild` context;

    :return: a list containing the default dependencies to primary
        archive.
    """
    if build.archive.purpose in ALLOW_RELEASE_BUILDS:
        primary_pockets = pocket_dependencies[
            default_pocket_dependency]
        primary_components = component_dependencies[
            default_component_dependency_name]
    else:
        primary_pockets = pocket_dependencies[build.pocket]
        primary_components = get_components_for_building(build)

    primary_dependencies = []
    for pocket in primary_pockets:
        primary_dependencies.append(
            (build.distribution.main_archive, pocket, primary_components)
            )

    return primary_dependencies
