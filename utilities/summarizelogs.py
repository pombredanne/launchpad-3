#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# parselogs.py
# Christian Reis <kiko@async.com.br>
#
# Parses Launchpad error logs and returns a list of most frequent errors

import re
import pprint
import sys
import time
import datetime

COUNT = 10
LAST_DAYS = 7

def init_or_set(d, v):
    if d.has_key(v):
        d[v] += 1
    else:
        d[v] = 1

def init_list_or_set(d, v, e):
    if d.has_key(v):
        d[v][e] = 1
    else:
        d[v] = {e: 1}

if len(sys.argv) == 1:
    lognames = ["launchpad1.log", "launchpad2.log"]
else:
    lognames = sys.argv[1:]

exceptions = {}
expired = {}
url_table = {}

now = datetime.datetime.fromtimestamp(time.time())
for logname in lognames:
    text = open(logname).read()
    errors = text.split("------")
    for error in errors:
        error = error.strip()
        if not error:
            continue

        fullerror = error
        error = error.split("\n")[-1].strip()
        first_line = fullerror.split("\n")[0]

        date = first_line.split(" ")[0]
        # XXX kiko 2005-10-17: handle timezone properly; it kinda sucks that
        # we have no way of knowing what timezone the log originates from.
        # For now I hack around this by assuming timezone is UTC.
        ts = time.strftime("%s", time.strptime(date, "%Y-%m-%dT%H:%M:%S"))
        then = datetime.datetime.fromtimestamp(float(ts))
        if now - then > datetime.timedelta(days=LAST_DAYS):
            continue

        if " WARNING " in error:
            continue
        extra = " ".join(first_line.split()[3:])
        if "RequestExpired:" in error:
            error = "RequestExpired: %s" % extra
            init_or_set(expired, error)
            continue
        if re.search("0x[abcdef0-9]+", error):
            error = re.sub("0x[abcdef0-9]+", "INSTANCE-ID", error)
        init_or_set(exceptions, error)
        init_list_or_set(url_table, error, extra)

values = exceptions.items()
values.sort(key=lambda x: x[1], reverse=True)

print
print "=== Top %d exceptions in the past %d days ===" % (COUNT, LAST_DAYS)
print
for exc, count in values[:COUNT]:
    print count, "\t", exc
    print "\t\t", "\n\t\t".join(url_table[exc].keys()[:10])

values = expired.items()
values.sort(key=lambda x: x[1], reverse=True)

print
print
print "=== Top %d timed out pages in the past %d days ===" % (COUNT, LAST_DAYS)
print
for url, count in values[:COUNT]:
    print count, "\t", url


