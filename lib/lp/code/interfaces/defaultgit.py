# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for objects that have a default Git repository.

A default Git repository is a repository that's somehow officially related
to an object.  It might be a project, a distribution source package, or a
combination of one of those with an owner to represent that owner's default
repository for that target.
"""

__metaclass__ = type
__all__ = [
    'ICanHasDefaultGitRepository',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )


class ICanHasDefaultGitRepository(Interface):
    """Something that has a default Git repository."""

    context = Attribute("The object that can have a default Git repository.")
    path = Attribute(
        "The path for the default Git repository. "
        "Note that this will be set even if there is no default repository.")
