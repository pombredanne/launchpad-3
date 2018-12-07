# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces relating to targets of Git repositories."""

__metaclass__ = type

__all__ = [
    'IHasGitRepositories',
    ]

from lazr.restful.declarations import export_as_webservice_entry
from zope.interface import Interface


class IHasGitRepositories(Interface):
    """An object that has related Git repositories.

    A project contains Git repositories, a source package on a distribution
    contains Git repositories, and a person contains "personal" Git
    repositories.
    """

    export_as_webservice_entry(
        singular_name="git_target", plural_name="git_targets", as_of="devel")
