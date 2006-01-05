#!/usr/bin/python

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

class CompilationError(Exception):
    def __init__(self, message, tb_info):
        self.message = message
        self.tb_info = tb_info

def find_python_files(top_path):
    for dirpath, dirnames, filenames in os.walk(top_path):
        for filename in filenames:
            if filename.endswith('.py'):
                yield os.path.join(dirpath, filename)

def check_file(filename):
    """Return a list of pyflakes messages for a Python file."""

    code = open(filename).read()

    try:
        tree = compiler.parse(code)
    except (SyntaxError, IndentationError), e:
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

def make_report(results):
    for result in results:
        if result.flakiness == Flakiness.GOOD:
            continue

        if result.flakiness == Flakiness.COMPILE_FAILED:
            yield '%s: Failed to compile:' % result.filename

            for message in result.messages:
                yield '    ' + str(message)
        elif result.flakiness == Flakiness.FLAKY:
            yield '%s:' % result.filename

            for message in result.messages:
                yield '    line ' + str(message)[len(result.filename)+1:]

        yield ''

def make_statistics(results):
    statistics = {
        'files_total' : 0,
        'files_compile_failed': 0,
        'files_flaky': 0,
        'files_good': 0,
        'messages_total': 0,
        'messages_undefined_name': 0,
        'messages_unused_import': 0,
        'messages_import_star': 0,
        'messages_redefined_unused': 0,
        }

    message_classes = {
        pyflakes.messages.UndefinedName: 'messages_undefined_name',
        pyflakes.messages.UnusedImport: 'messages_unused_import',
        pyflakes.messages.ImportStarUsed: 'messages_import_star',
        pyflakes.messages.RedefinedWhileUnused: 'messages_redefined_unused',
        }

    for result in results:
        statistics['files_total'] += 1

        if result.flakiness == Flakiness.COMPILE_FAILED:
            statistics['files_compile_failed'] += 1
        elif result.flakiness == Flakiness.FLAKY:
            statistics['files_flaky'] += 1
            statistic = None

            for message in result.messages:
                statistics['messages_total'] += 1
                statistic = message_classes[message.__class__]
                statistics[statistic] += 1
        elif result.flakiness == Flakiness.GOOD:
            statistics['files_good'] += 1

    return statistics

def make_statistics_summary(statistics):
    return [
        'Files checked: %d' % statistics['files_total'],
        'Files that failed to compile: %d' %
            statistics['files_compile_failed'],
        'Good files: %d' % statistics['files_good'],
        'Flaky files: %d' % statistics['files_flaky'],
        ' - Undefined name: %d' % statistics['messages_undefined_name'],
        ' - Unused imports: %d' % statistics['messages_unused_import'],
        ' - * imported: %d' % statistics['messages_import_star'],
        ' - Unused name redefined: %d' %
            statistics['messages_redefined_unused'],
        ' - Problems total: %d' %
            statistics['messages_total'],
        ]

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
        reulsts.append(check_file(filename))
        results.append(result)
        sys.stderr.write('.')
        sys.stderr.flush()

    sys.stderr.write('\nDone\n\n')
    statistics = make_statistics(results)

    for line in make_report(results):
        print line

    for line in make_statistics_summary(statistics):
        print line

    if statistics['files_compile_failed'] + statistics['files_flaky'] > 0:
        return 1
    else:
        return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

