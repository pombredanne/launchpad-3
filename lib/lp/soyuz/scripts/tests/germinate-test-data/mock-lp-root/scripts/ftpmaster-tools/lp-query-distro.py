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


if __name__ == "__main__":
        # There is only a very limited subset of arguments that we support,
        # test for it and error if it looks wrong
        if len(sys.argv) != 2:
                error_and_exit()
        distro = sys.argv[1]
        if distro == "development":
                print "natty"
        elif distro == "supported":
                print "hardy jaunty karmic lucid maverick"
        else:
                error_and_exit()
