# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'determine_architectures_to_build',
    ]

from collections import Counter

import six

from lp.services.helpers import english_list


class SnapArchitecturesParserError(Exception):
    """Base class for all exceptions in this module."""


class MissingPropertyError(SnapArchitecturesParserError):
    """Error for when an expected property is not present in the YAML."""

    def __init__(self, prop):
        super(MissingPropertyError, self).__init__(
            "Architecture specification is missing the {!r} property".format(
                prop))
        self.property = prop


class IncompatibleArchitecturesStyleError(SnapArchitecturesParserError):
    """Error for when architectures mix incompatible styles."""

    def __init__(self):
        super(IncompatibleArchitecturesStyleError, self).__init__(
            "'architectures' must either be a list of strings or dicts, not "
            "both")


class DuplicateBuildOnError(SnapArchitecturesParserError):
    """Error for when multiple `build-on`s include the same architecture."""

    def __init__(self, duplicates):
        super(DuplicateBuildOnError, self).__init__(
            "{} {} present in the 'build-on' of multiple items".format(
                english_list(duplicates),
                "is" if len(duplicates) == 1 else "are"))


class UnsupportedBuildOnError(SnapArchitecturesParserError):
    """Error for when a requested architecture is not supported."""

    def __init__(self, build_on):
        super(UnsupportedBuildOnError, self).__init__(
            "build-on specifies no supported architectures: {!r}".format(
                build_on))
        self.build_on = build_on


class SnapArchitecture:
    """A single entry in the snapcraft.yaml 'architectures' list."""

    def __init__(self, build_on, run_on=None, build_error=None):
        """Create a new architecture entry.

        :param build_on: string or list; build-on property from
            snapcraft.yaml.
        :param run_on: string or list; run-on property from snapcraft.yaml
            (defaults to build_on).
        :param build_error: string; build-error property from
            snapcraft.yaml.
        """
        self.build_on = (
            [build_on] if isinstance(build_on, six.string_types) else build_on)
        if run_on:
            self.run_on = (
                [run_on] if isinstance(run_on, six.string_types) else run_on)
        else:
            self.run_on = self.build_on
        self.build_error = build_error

    @classmethod
    def from_dict(cls, properties):
        """Create a new architecture entry from a dict."""
        try:
            build_on = properties["build-on"]
        except KeyError:
            raise MissingPropertyError("build-on")

        return cls(
            build_on=build_on, run_on=properties.get("run-on"),
            build_error=properties.get("build-error"))


class SnapBuildInstance:
    """A single instance of a snap that should be built.

    It has two useful attributes:

      - architecture: The architecture tag that should be used to build the
            snap.
      - required: Whether or not failure to build should cause the entire
            set to fail.
    """

    def __init__(self, architecture, supported_architectures):
        """Construct a new `SnapBuildInstance`.

        :param architecture: `SnapArchitecture` instance.
        :param supported_architectures: List of supported architectures,
            sorted by priority.
        """
        try:
            self.architecture = next(
                arch for arch in supported_architectures
                if arch in architecture.build_on)
        except StopIteration:
            raise UnsupportedBuildOnError(architecture.build_on)

        self.required = architecture.build_error != "ignore"


def determine_architectures_to_build(snapcraft_data, supported_arches):
    """Return a list of architectures to build based on snapcraft.yaml.

    :param snapcraft_data: A parsed snapcraft.yaml.
    :param supported_arches: An ordered list of all architecture tags that
        we can create builds for.
    :return: a list of `SnapBuildInstance`s.
    """
    architectures_list = snapcraft_data.get("architectures")

    if architectures_list:
        # First, determine what style we're parsing.  Is it a list of
        # strings or a list of dicts?
        if all(isinstance(a, six.string_types) for a in architectures_list):
            # If a list of strings (old style), then that's only a single
            # item.
            architectures = [SnapArchitecture(build_on=architectures_list)]
        elif all(isinstance(arch, dict) for arch in architectures_list):
            # If a list of dicts (new style), then that's multiple items.
            architectures = [
                SnapArchitecture.from_dict(a) for a in architectures_list]
        else:
            # If a mix of both, bail.  We can't reasonably handle it.
            raise IncompatibleArchitecturesStyleError()
    else:
        # If no architectures are specified, build one for each supported
        # architecture.
        architectures = [
            SnapArchitecture(build_on=a) for a in supported_arches]

    # Ensure that multiple `build-on` items don't include the same
    # architecture; this is ambiguous and forbidden by snapcraft.  Checking
    # this here means that we don't get duplicate supported_arch results
    # below.
    build_ons = Counter()
    for arch in architectures:
        build_ons.update(arch.build_on)
    duplicates = {arch for arch, count in build_ons.items() if count > 1}
    if duplicates:
        raise DuplicateBuildOnError(duplicates)

    architectures_to_build = []
    for arch in architectures:
        try:
            architectures_to_build.append(
                SnapBuildInstance(arch, supported_arches))
        except UnsupportedBuildOnError:
            # Snaps are allowed to declare that they build on architectures
            # that Launchpad doesn't currently support (perhaps they're
            # upcoming, or perhaps they used to be supported).  We just
            # ignore those.
            pass
    return architectures_to_build
