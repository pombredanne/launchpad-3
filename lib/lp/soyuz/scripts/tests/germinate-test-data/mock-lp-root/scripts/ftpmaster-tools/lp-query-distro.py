#!/usr/bin/python
#
# This is a mock version of the lp-query-distro.py script that
# returns static data so that the cron.germinate shell script
# can be tested.

import sys


def error_and_exit():
    sys.stderr.write("ERROR: I'm a mock, I only support 'development' "
                        "and 'supported' as argument\n")
    sys.exit(1)


def main(args):
    # There is only a very limited subset of arguments that we support,
    # test for it and error if it looks wrong
    if len(args) == 2:
        distro = args[1]
        if distro == "development":
                return "natty"
        elif distro == "supported":
                return "hardy jaunty karmic lucid maverick"
    elif len(args) == 4 and args[1] == '-s' and args[3] == 'archs':
        return "i386 amd64 powerpc armel"
    error_and_exit()


if __name__ == "__main__":
    print main(sys.argv)
