#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""top-tests.py - Report about slowest tests in the test suite.

It parses the output of the testrunner run with -vvv and collects
statistics about the test run.
"""

__metaclass__ = type

import re
import operator
import os
import sys

LEN = 20

class ParseException(Exception):
    """Exception raised when there is an error while parsing a log file."""


class TestRunnerStats:
    """Encapsulates information about the time it took to run a testsuite."""

    LAYER_STARTS_RE = re.compile(r'Running (.+) tests:')

    LAYER_ENDS_RE = re.compile(
        r'  Ran (\d+) tests with (\d+) failures and (\d+) errors in ([\d.]+) '
        'seconds.')

    SETUP_RE = re.compile(r'  Set up ([\w.]+) in ([\d.]+) seconds.')

    TEARDOWN_RE = re.compile(r'  Tear down ([\w.]+) in ([\d.]+) seconds.')

    UNSUPPORTED_TEARDOWN_RE = re.compile(
        r'  Tear down ([\w.]+) ... not supported')

    # We are not restricting this to the standard python identifiers because
    # some doctest unittest or generated tests could contain funky names.
    PYTHON_TEST_RE = re.compile(r'([^\( ]+) ?\(([^\)]+)\)')

    MS_RE = re.compile(r'\s*\(([\d.]+) ms\)$')

    TOTAL_RE = re.compile(r'Total: (\d+) tests, (\d+) failures, (\d+) errors')

    # List of strings/patterns to attempt at matching.
    # The second element in the tuple is the method to call when the start of
    # the current line matches the string or the pattern.
    MATCH_LIST = [
        ('Running tests at level', 'handleStartTestRunner'),
        (LAYER_STARTS_RE, 'handleLayerStart'),
        (LAYER_ENDS_RE, 'handleLayerEnd'),
        (SETUP_RE, 'handleLayerSetUp'),
        (TEARDOWN_RE, 'handleLayerTearDown'),
        (UNSUPPORTED_TEARDOWN_RE, 'handleUnsupportedTearDown'),
        ('  Running:', None),
        ('Tearing down left over layers:', 'handleFinalTearDown'),
        (MS_RE, 'handleTestRuntime'),
        (LAYER_ENDS_RE, 'handleLayerEnd'),
        (TEARDOWN_RE, 'handleLayerTearDown'),
        (TOTAL_RE, 'handleTotal'),
        ('    ', 'handleTestRun'),
        (None, 'handleGarbage'),
        ]

    def __init__(self, logfile):
        """Create a new TestRunnerStats from a log file.

        :param logfile: Open file-like object containing the log of the test
            suite. That should have been generated at -vvv for maximum
            information.
        :raise ParseException: when the log file doesn't contain a testrunner
            log, or couldn't be parsed for some other reasons.
        """
        self.logfile = logfile
        self._parse()

    def _parse(self):
        """Extract timing information from the log file."""
        self.layers = {}
        self.ignored_lines = []
        self.current_layer = None
        self.last_test = None

        end_of_tests = False
        while not end_of_tests:
            line = self.logfile.readline()
            if not line:
                break
            for match, action in self.MATCH_LIST:
                found = False
                if isinstance(match, basestring):
                    if line.startswith(match):
                        found = True
                elif match is None:
                    # None indicates the default action.
                    found = True
                elif getattr(match, 'match', None):
                    found = match.match(line)
                if found:
                    # Action is the name of the method to call.
                    # If it returns False, stop parsing.
                    if action is not None:
                        end_of_tests = getattr(self, action)(line, found)
                    break

        if not end_of_tests:
            raise ParseException('End of file before end of test run.')

    def handleStartTestRunner(self, line, ignored):
        """Switch the the layer state."""

    def handleLayerStart(self, line, match):
        """Create a new stats container for the layer."""
        layer_name = match.group(1)
        self.current_layer = self.getLayer(layer_name)

    def handleLayerEnd(self, line, match):
        """Collect the total runtime for the layer tests."""
        tests_run = match.group(1)
        runtime = match.group(4)
        self.current_layer.collectEndResults(tests_run, runtime)

    def handleLayerSetUp(self, line, match):
        """Collect the runtime for the layer set up."""
        layer_name = match.group(1)
        runtime = float(match.group(2))
        self.getLayer(layer_name).collectSetUp(runtime)

    def handleLayerTearDown(self, line, match):
        """Collect the runtime for the layer tear down."""
        layer_name = match.group(1)
        runtime = float(match.group(2))
        self.getLayer(layer_name).collectTearDown(runtime)

    def handleUnsupportedTearDown(self, line, match):
        """Flag that tear down was unsupported."""
        layer_name = match.group(1)
        self.getLayer(layer_name).collectUnsupportedTearDown()

    def handleFinalTearDown(self, line, match):
        """Switch to teardown state."""

    def handleTestRun(self, line, ignored):
        """Collect that a test was run."""
        # If we didn't saw the last test runtime, we are probably
        # in a stack trace or something like that. So treat it as garbage.
        if self.last_test is not None and not self.last_test_complete:
            if self.MS_RE.search(line) is None:
                self.handleGarbage(line, ignored)
                return
            else:
                # It happens that a test doesn't output timing information.
                # But other tests after that will. 
                # We are probably encountering such a case.
                pass
        line = line[4:]
        if '/' in line:
            if ' ' in line:
                doctest, line = line.split(' ', 1)
            else:
                doctest = line
                line = '\n'
            self.last_test = DocTestStats(doctest)
        else:
            match = self.PYTHON_TEST_RE.match(line)
            if match:
                self.last_test = PythonTestStats(
                    match.group(1), match.group(2))
            else:
                raise ParseException("can't parse test name: %s" % line)
            line = line[match.end():]
        self.current_layer.collectTest(self.last_test)

        # If the runtime isn't on this line, it means that there was output
        # by the test, so we'll find the runtime info later on.
        match = self.MS_RE.search(line)
        if match:
            self.last_test_complete = True
            self.last_test.runtime = float(match.group(1))
        else:
            self.last_test_complete = False
            self.last_test.collectGarbage(line)

    def handleGarbage(self, line, ignored):
        """Save the log output by the test."""
        if self.last_test is not None:
            self.last_test.collectGarbage(line)
        else:
            self.ignored_lines.append(line)

    def handleTestRuntime(self, line, match):
        """Collect the broken test runtime."""
        if self.last_test is not None:
            self.last_test.runtime = float(match.group(1))
            self.last_test_complete = True
        else:
            self.ignored_lines.append(line)

    def handleTotal(self, line, match):
        """Action invoked when the final line is encountered."""
        self.current_layer = None
        self.last_test = None
        return True

    def getLayer(self, layer_name):
        """Return the layer with name.

        Create and return an empty layer if it doesn't exists.
        """
        if layer_name not in self.layers:
            self.layers[layer_name] = TestLayerStats(layer_name)
        return self.layers[layer_name]

    def getTestsIter(self):
        """Return an iterator over all tests."""
        for layer in self.layers.values():
            for test in layer.tests:
                yield test

    @property
    def total_runtime(self):
        """Number of seconds used to run the whole test suite."""
        return sum([layer.total_runtime for layer in self.layers.values()])

    @property
    def tests_count(self):
        """Number of tests in the test suite."""
        return sum([len(layer.tests) for layer in self.layers.values()])


class TestLayerStats:
    """Contain all the tests that were run in the layer."""

    name = None
    unsupported_tear_downs = 0

    tests_runtime = 0

    def __init__(self, name):
        """Create a new stats container."""
        self.name = name
        self.tests = []
        self.set_ups = []
        self.tear_downs = []

    @property
    def total_runtime(self):
        """Return the runtime (including fixture) in this layer."""
        return self.tests_runtime + sum(self.set_ups) + sum(self.tear_downs)

    def collectTest(self, test):
        """Call when a test was run in the layer."""
        self.tests.append(test)

    def collectEndResults(self, tests_run, runtime):
        """Called when all the tests in the layer were run."""
        self.tests_runtime = float(runtime)
        self.tests_count = int(tests_run)

    def collectSetUp(self, runtime):
        """Called when the layer was set up."""
        self.set_ups.append(runtime)

    def collectTearDown(self, runtime):
        """Called when the layer was torn down."""
        self.tear_downs.append(runtime)

    def collectUnsupportedTearDown(self):
        """Called when the layer couldn't be torn down."""
        self.unsupported_tear_downs += 1

    def __iter__(self):
        """Return an iterator over the tests run in this layer."""
        return iter(self.tests)


class TestStats:
    """Base class for a test stats."""

    name = None
    runtime = 0

    def __init__(self):
        self._garbage = []

    @property
    def garbage(self):
        """Return the garbage output by the test."""
        return "".join(self._garbage)

    def collectGarbage(self, line):
        self._garbage.append(line)


class PythonTestStats(TestStats):
    """Stats for a regular python unit test."""

    def __init__(self, method, module):
        super(PythonTestStats, self).__init__()
        self.method = method
        self.module = module

    @property
    def name(self):
        """Return the full name of the test."""
        return "%s.%s" % (self.module, self.method)


class DocTestStats(TestStats):
    """Stats for a doctest."""

    def __init__(self, filename):
        super(DocTestStats, self).__init__()
        self.filename = filename

    @property
    def name(self):
        """Remove the PQM directory from the name."""
        index = self.filename.find("lib/canonical")
        if index != -1:
            filename = self.filename[index:]
        else:
            filename = self.filename
        return os.path.normpath(filename)


class PQMLog:
    """Encapsulates information about a PQM log."""

    def __init__(self, logfile):
        """Create a new PQMLog instance.

        :param logfile: Path to the PQM log.
        """
        self.logfile = logfile
        self.fixtures_profile = []

        self._parse()

    def _parse(self):
        """Parse a PQM log file.

        Extract the branch name, the time each tests took as well as the
        time spent in the layers.
        """
        self.branch = "Unknown"
        profile = self.fixtures_profile

        logfile = open(self.logfile)
        while True:
            line = logfile.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            if line.startswith("Executing star-merge"):
                self.branch = line.split(" ")[2]
            elif " calls taking " in line:
                if "s." not in line:
                    continue
                values = line.split(" ")
                runtime = float(values[-1][:-2])
                profile.append((runtime, values[0]))
            elif line.startswith("Executing pre-commit hook"):
                self.testrunner_stats = TestRunnerStats(logfile)


def main(argv):
    """Parse a PQM log file."""
    if len(sys.argv) > 1:
        logfile = sys.argv[1]
    else:
        logfile = find_latest_successful_merge()
    print_report(PQMLog(logfile))


def find_latest_successful_merge():
    """Return the latest PQM log that contain a successful merge.

    Look into the current directory for the log files.
    """
    cmd = "ls -at | head -10 | xargs grep -l 'star-merge succeeded'"
    p = os.popen(cmd)
    logfile_name = p.readlines()[0].strip()
    p.close()
    return logfile_name


def print_report(pqm_log, out=sys.stdout):
    """Print the report on STDOUT."""

    print >>out, "Log: %s" % pqm_log.logfile
    print >>out, "Branch: %s" % pqm_log.branch

    stats = pqm_log.testrunner_stats

    top_tests =  list(stats.getTestsIter())
    top_tests.sort(key=operator.attrgetter('runtime'), reverse=True)

    total_runtime = stats.total_runtime
    tests_count = stats.tests_count

    print >>out
    print >>out, "Top %d tests taking the longest time" % LEN
    print >>out, "===================================="
    print
    top_runtime = 0.0
    for test in top_tests[:LEN]:
        percent = test.runtime / total_runtime * 100
        top_runtime += test.runtime
        print >>out, "%6.2f (%.1f%%) %s" % (test.runtime, percent, test.name)
    print >>out
    test_percent = LEN / float(tests_count) * 100
    time_percent = top_runtime / total_runtime * 100
    print >>out, (
        "Top %s of %s (%.1f%%) tests taking %ss of %ss (%.1f%%)"
        % (LEN, tests_count, test_percent, top_runtime, total_runtime,
           time_percent))
    print >>out

    print >>out, "Tests and runtime by layer"
    print >>out, "=========================="
    print >>out

    layers = stats.layers.values()
    layers.sort(key=operator.attrgetter('total_runtime'), reverse=True)
    for layer in layers:
        if len(layer.tests) == 0:
            continue
        runtime_percent = layer.tests_runtime / total_runtime * 100
        layer_name = layer.name.split('.')[-1]
        print "%7.2f (%4.1f%%) %4d tests (%5.2fs/t) %s" % (
            layer.tests_runtime, runtime_percent, len(layer.tests),
            layer.tests_runtime / len(layer.tests), layer_name)


    print >>out
    print >>out, "Slowest fixture methods"
    print >>out, "======================="
    print >>out

    profile = list(pqm_log.fixtures_profile)
    profile.sort(reverse=True)
    print >>out
    fixture_runtime = 0
    for runtime, method in profile:
        runtime_percent = runtime / total_runtime * 100
        print >>out, "%7.2f (%4.1f%%) %s" % (runtime, runtime_percent, method)
        fixture_runtime += runtime

    print >>out
    print >>out, "Fixture overhead %ss (%.1f%%)" % (
        fixture_runtime, fixture_runtime / total_runtime * 100)
    print >>out

    tests_with_garbage = 0
    garbage_lines_count = 0
    for test in stats.getTestsIter():
        if len(test.garbage):
            tests_with_garbage += 1
            garbage_lines_count += test.garbage.strip().count('\n')+1

    print >>out, "%d tests output %d warning lines." % (
        tests_with_garbage, garbage_lines_count)
    print >>out, "Ignored %d lines in the testrunner output." % len(
        stats.ignored_lines)
    print >>out


if __name__ == '__main__':
    main(sys.argv)
