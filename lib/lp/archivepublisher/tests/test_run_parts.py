# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test publisher run-parts handling."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import os.path

from fixtures import MonkeyPatch
from testtools.matchers import (
    ContainsDict,
    Equals,
    FileExists,
    )

from lp.archivepublisher.run_parts import (
    execute_subprocess,
    find_run_parts_dir,
    run_parts,
    )
from lp.services.config import config
from lp.services.log.logger import DevNullLogger
from lp.testing import TestCase
from lp.testing.fakemethod import FakeMethod


class RunPartsMixin:
    """Helper for run-parts tests."""

    def enableRunParts(self, parts_directory=None, distribution_name="ubuntu"):
        """Set up for run-parts execution.

        :param parts_directory: Base location for the run-parts directories.
            If omitted, a temporary directory will be used.
        :param distribution_name: The name of the distribution to set up.
        """
        if parts_directory is None:
            parts_directory = self.makeTemporaryDirectory()
            for name in ("sign.d", "publish-distro.d", "finalize.d"):
                os.makedirs(os.path.join(
                    parts_directory, distribution_name, name))
        self.parts_directory = parts_directory
        self.pushConfig("archivepublisher", run_parts_location=parts_directory)


class TestFindRunPartsDir(TestCase, RunPartsMixin):

    def test_finds_runparts_directory(self):
        self.enableRunParts()
        self.assertEqual(
            os.path.join(
                config.root, self.parts_directory, "ubuntu", "finalize.d"),
            find_run_parts_dir("ubuntu", "finalize.d"))

    def test_ignores_blank_config(self):
        self.enableRunParts("")
        self.assertIs(None, find_run_parts_dir("ubuntu", "finalize.d"))

    def test_ignores_none_config(self):
        self.enableRunParts("none")
        self.assertIs(None, find_run_parts_dir("ubuntu", "finalize.d"))

    def test_ignores_nonexistent_directory(self):
        self.enableRunParts()
        self.assertIs(None, find_run_parts_dir("nonexistent", "finalize.d"))


class TestExecuteSubprocess(TestCase):

    def test_executes_shell_command(self):
        marker = os.path.join(self.makeTemporaryDirectory(), "marker")
        execute_subprocess(["touch", marker])
        self.assertThat(marker, FileExists())

    def test_reports_failure_if_requested(self):
        class ArbitraryFailure(Exception):
            """Some exception that's not likely to come from elsewhere."""

        self.assertRaises(
            ArbitraryFailure,
            execute_subprocess, ["/bin/false"], failure=ArbitraryFailure())

    def test_does_not_report_failure_if_not_requested(self):
        # The test is that this does not fail:
        execute_subprocess(["/bin/false"])


class TestRunParts(TestCase, RunPartsMixin):

    def test_runs_parts(self):
        self.enableRunParts()
        execute_subprocess_fixture = self.useFixture(MonkeyPatch(
            "lp.archivepublisher.run_parts.execute_subprocess", FakeMethod()))
        run_parts("ubuntu", "finalize.d", log=DevNullLogger(), env={})
        self.assertEqual(1, execute_subprocess_fixture.new_value.call_count)
        args, kwargs = execute_subprocess_fixture.new_value.calls[-1]
        self.assertEqual(
            (["run-parts", "--",
              os.path.join(self.parts_directory, "ubuntu/finalize.d")],),
            args)

    def test_passes_parameters(self):
        self.enableRunParts()
        execute_subprocess_fixture = self.useFixture(MonkeyPatch(
            "lp.archivepublisher.run_parts.execute_subprocess", FakeMethod()))
        key = self.factory.getUniqueString()
        value = self.factory.getUniqueString()
        run_parts(
            "ubuntu", "finalize.d", log=DevNullLogger(), env={key: value})
        args, kwargs = execute_subprocess_fixture.new_value.calls[-1]
        self.assertThat(kwargs["env"], ContainsDict({key: Equals(value)}))
