# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )
from testtools.matchers import HasLength

from lp.snappy.adapters.buildarch import (
    determine_architectures_to_build,
    SnapArchitecture,
    SnapBuildInstance,
    UnsupportedBuildOnError,
    )
from lp.testing import TestCase


class TestSnapArchitecture(WithScenarios, TestCase):

    scenarios = [
        ("lists", {
            "architectures": {"build-on": ["amd64"], "run-on": ["amd64"]},
            "expected_build_on": ["amd64"],
            "expected_run_on": ["amd64"],
            "expected_build_error": None,
            }),
        ("strings", {
            "architectures": {"build-on": "amd64", "run-on": "amd64"},
            "expected_build_on": ["amd64"],
            "expected_run_on": ["amd64"],
            "expected_build_error": None,
            }),
        ("no run-on", {
            "architectures": {"build-on": ["amd64"]},
            "expected_build_on": ["amd64"],
            "expected_run_on": ["amd64"],
            "expected_build_error": None,
            }),
        ("not required", {
            "architectures": {
                "build-on": ["amd64"],
                "run-on": "amd64",
                "build-error": "ignore"},
            "expected_build_on": ["amd64"],
            "expected_run_on": ["amd64"],
            "expected_build_error": "ignore",
            }),
        ]

    def test_architecture(self):
        architecture = SnapArchitecture.from_dict(self.architectures)
        self.assertEqual(self.expected_build_on, architecture.build_on)
        self.assertEqual(self.expected_run_on, architecture.run_on)
        self.assertEqual(self.expected_build_error, architecture.build_error)


class TestSnapBuildInstance(WithScenarios, TestCase):

    # Single-item scenarios taken from the architectures document:
    # https://forum.snapcraft.io/t/architectures/4972
    scenarios = [
        ("i386", {
            "architecture": SnapArchitecture(
                build_on="i386", run_on=["amd64", "i386"]),
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected_architecture": "i386",
            "expected_required": True,
            }),
        ("amd64", {
            "architecture": SnapArchitecture(build_on="amd64", run_on="all"),
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected_architecture": "amd64",
            "expected_required": True,
            }),
        ("amd64 priority", {
            "architecture": SnapArchitecture(
                build_on=["amd64", "i386"], run_on="all"),
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected_architecture": "amd64",
            "expected_required": True,
            }),
        ("i386 priority", {
            "architecture": SnapArchitecture(
                build_on=["amd64", "i386"], run_on="all"),
            "supported_architectures": ["i386", "amd64", "armhf"],
            "expected_architecture": "i386",
            "expected_required": True,
            }),
        ("optional", {
            "architecture": SnapArchitecture(
                build_on="amd64", build_error="ignore"),
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected_architecture": "amd64",
            "expected_required": False,
            }),
        ]

    def test_build_instance(self):
        instance = SnapBuildInstance(
            self.architecture, self.supported_architectures)
        self.assertEqual(self.expected_architecture, instance.architecture)
        self.assertEqual(self.expected_required, instance.required)


class TestSnapBuildInstanceError(TestCase):

    def test_no_matching_arch_raises(self):
        architecture = SnapArchitecture(build_on="amd64", run_on="amd64")
        raised = self.assertRaises(
            UnsupportedBuildOnError, SnapBuildInstance, architecture, ["i386"])
        self.assertEqual(["amd64"], raised.build_on)


class TestDetermineArchitecturesToBuild(WithScenarios, TestCase):

    # Scenarios taken from the architectures document:
    # https://forum.snapcraft.io/t/architectures/4972
    scenarios = [
        ("none", {
            "architectures": None,
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected": [
                {"architecture": "amd64", "required": True},
                {"architecture": "i386", "required": True},
                {"architecture": "armhf", "required": True},
                ],
            }),
        ("i386", {
            "architectures": [
                {"build-on": "i386", "run-on": ["amd64", "i386"]},
                ],
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected": [{"architecture": "i386", "required": True}],
            }),
        ("amd64", {
            "architectures": [{"build-on": "amd64", "run-on": "all"}],
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected": [{"architecture": "amd64", "required": True}],
            }),
        ("amd64 and i386", {
            "architectures": [
                {"build-on": "amd64", "run-on": "amd64"},
                {"build-on": "i386", "run-on": "i386"},
                ],
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected": [
                {"architecture": "amd64", "required": True},
                {"architecture": "i386", "required": True},
                ],
            }),
        ("amd64 and i386 shorthand", {
            "architectures": [
                {"build-on": "amd64"},
                {"build-on": "i386"},
                ],
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected": [
                {"architecture": "amd64", "required": True},
                {"architecture": "i386", "required": True},
                ],
            }),
        ("amd64, i386, and armhf", {
            "architectures": [
                {"build-on": "amd64", "run-on": "amd64"},
                {"build-on": "i386", "run-on": "i386"},
                {
                    "build-on": "armhf",
                    "run-on": "armhf",
                    "build-error": "ignore",
                    },
                ],
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected": [
                {"architecture": "amd64", "required": True},
                {"architecture": "i386", "required": True},
                {"architecture": "armhf", "required": False},
                ],
            }),
        ("amd64 priority", {
            "architectures": [
                {"build-on": ["amd64", "i386"], "run-on": "all"},
                ],
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected": [{"architecture": "amd64", "required": True}],
            }),
        ("i386 priority", {
            "architectures": [
                {"build-on": ["amd64", "i386"], "run-on": "all"},
                ],
            "supported_architectures": ["i386", "amd64", "armhf"],
            "expected": [{"architecture": "i386", "required": True}],
            }),
        ("old style i386 priority", {
            "architectures": ["amd64", "i386"],
            "supported_architectures": ["i386", "amd64", "armhf"],
            "expected": [{"architecture": "i386", "required": True}],
            }),
        ("old style amd64 priority", {
            "architectures": ["amd64", "i386"],
            "supported_architectures": ["amd64", "i386", "armhf"],
            "expected": [{"architecture": "amd64", "required": True}],
            }),
    ]

    def test_parser(self):
        snapcraft_data = {"architectures": self.architectures}
        build_instances = determine_architectures_to_build(
            snapcraft_data, self.supported_architectures)
        self.assertThat(build_instances, HasLength(len(self.expected)))
        for instance in build_instances:
            self.assertIn(instance.__dict__, self.expected)


load_tests = load_tests_apply_scenarios
