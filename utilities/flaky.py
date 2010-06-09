#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run pyflakes checks on a set of files."""

import compiler
import os
import sys
import traceback

import pyflakes


class Flakiness:
    COMPILE_FAILED = 0
    FLAKY = 1
    GOOD = 2


class PyflakesResult:
    def __init__(self, filename, flakiness, messages):
        self.filename = filename
        self.flakiness = flakiness
        self.messages = messages

    def make_report(self):
        """Generate a text report for the result.

        Yields a line of text for each line of the report.
        """

        if self.flakiness == Flakiness.GOOD:
            return

        if self.flakiness == Flakiness.COMPILE_FAILED:
            yield '%s: Failed to compile:' % self.filename

            for message in self.messages:
                yield '    ' + str(message)
        elif self.flakiness == Flakiness.FLAKY:
            yield '%s:' % self.filename

            for message in self.messages:
                yield '    line ' + str(message)[len(self.filename)+1:]

        yield ''


class PyflakesStatistics:
    """Counts of pyflakes messages over multiple Python files."""

    message_classes = {
        pyflakes.messages.UndefinedName: 'messages_undefined_name',
        pyflakes.messages.UnusedImport: 'messages_unused_import',
        pyflakes.messages.ImportStarUsed: 'messages_import_star',
        pyflakes.messages.RedefinedWhileUnused: 'messages_redefined_unused',
        }

    def __init__(self):
        self.files_total = 0
        self.files_compile_failed = 0
        self.files_flaky = 0
        self.files_good = 0
        self.messages_total = 0
        self.messages_undefined_name = 0
        self.messages_unused_import = 0
        self.messages_import_star = 0
        self.messages_redefined_unused = 0

    def add_result(self, result):
        self.files_total += 1

        if result.flakiness == Flakiness.GOOD:
            self.files_good += 1
        elif result.flakiness == Flakiness.COMPILE_FAILED:
            self.files_compile_failed += 1
        elif result.flakiness == Flakiness.FLAKY:
            self.files_flaky += 1
            statistic = None

            for message in result.messages:
                self.messages_total += 1

                # Increment the appropriate self.messages_* count.
                attr = PyflakesStatistics.message_classes[message.__class__]
                statistic = getattr(self, attr)
                setattr(self, attr, statistic + 1)

    def make_summary(self):
        return [
            'Files checked: %d' % self.files_total,
            'Files that failed to compile: %d' %
                self.files_compile_failed,
            'Good files: %d' % self.files_good,
            'Flaky files: %d' % self.files_flaky,
            ' - Undefined name: %d' % self.messages_undefined_name,
            ' - Unused imports: %d' % self.messages_unused_import,
            ' - * imported: %d' % self.messages_import_star,
            ' - Unused name redefined: %d' % self.messages_redefined_unused,
            ' - Problems total: %d' % self.messages_total,
            ]


def find_python_files(top_path):
    for dirpath, dirnames, filenames in os.walk(top_path):
        for filename in filenames:
            if filename.endswith('.py'):
                yield os.path.join(dirpath, filename)


def check_file(filename):
    """Return a list of pyflakes messages for a Python file."""

    source = open(filename).read()

    try:
        tree = compiler.parse(source)
    except (SyntaxError, IndentationError):
        tb_info = traceback.format_exception(*sys.exc_info())
        messages = [message[:-1] for message in tb_info]
        return PyflakesResult(filename, Flakiness.COMPILE_FAILED, messages)
    else:
        checker = pyflakes.Checker(tree, filename)
        messages = sorted(checker.messages, key=lambda message: message.lineno)

        if messages:
            return PyflakesResult(filename, Flakiness.FLAKY, messages)
        else:
            return PyflakesResult(filename, Flakiness.GOOD, messages)


def main(argv):
    if len(argv) < 2:
        print >>sys.stderr, 'Usage: %s path...' % argv[0]
        return 1

    files = []

    for path in argv[1:]:
        if os.path.isdir(path):
            files.extend(find_python_files(argv[1]))
        else:
            files.append(path)

    sys.stderr.write('Running pyflakes checks\n')
    results = []

    for filename in files:
        results.append(check_file(filename))
        sys.stderr.write('.')
        sys.stderr.flush()

    sys.stderr.write('\nDone\n\n')

    for result in results:
        for line in result.make_report():
            print line

    statistics = PyflakesStatistics()

    for result in results:
        statistics.add_result(result)

    for line in statistics.make_summary():
        print line

    if statistics.files_compile_failed + statistics.files_flaky > 0:
        return 1
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

