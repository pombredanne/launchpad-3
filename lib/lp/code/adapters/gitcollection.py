# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapters for different objects to Git repository collections."""

__metaclass__ = type
__all__ = [
    'git_collection_for_distribution',
    'git_collection_for_distro_source_package',
    'git_collection_for_person',
    'git_collection_for_person_distro_source_package',
    'git_collection_for_person_product',
    'git_collection_for_project',
    'git_collection_for_project_group',
    ]


from zope.component import getUtility

from lp.code.interfaces.gitcollection import IAllGitRepositories


def git_collection_for_project(project):
    """Adapt a product to a Git repository collection."""
    return getUtility(IAllGitRepositories).inProject(project)


def git_collection_for_project_group(project_group):
    """Adapt a project group to a Git repository collection."""
    return getUtility(IAllGitRepositories).inProjectGroup(project_group)


def git_collection_for_distribution(distribution):
    """Adapt a distribution to a Git repository collection."""
    return getUtility(IAllGitRepositories).inDistribution(distribution)


def git_collection_for_distro_source_package(distro_source_package):
    """Adapt a distro_source_package to a Git repository collection."""
    return getUtility(IAllGitRepositories).inDistributionSourcePackage(
        distro_source_package)


def git_collection_for_person(person):
    """Adapt a person to a Git repository collection."""
    return getUtility(IAllGitRepositories).ownedBy(person)


def git_collection_for_person_product(person_product):
    """Adapt a PersonProduct to a Git repository collection."""
    collection = getUtility(IAllGitRepositories).ownedBy(person_product.person)
    collection = collection.inProject(person_product.product)
    return collection


def git_collection_for_person_distro_source_package(person_dsp):
    """Adapt a PersonDistributionSourcePackage to a Git repository
    collection."""
    collection = getUtility(IAllGitRepositories).ownedBy(person_dsp.person)
    collection = collection.inDistributionSourcePackage(
        person_dsp.distro_source_package)
    return collection
