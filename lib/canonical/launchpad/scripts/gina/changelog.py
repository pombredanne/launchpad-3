# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Gina's changelog parser and muncher for great justice"""

import re, sys

first_re = re.compile(r"^[a-z][a-z0-9\\+\\.\\-]+ ")
prio_re = re.compile(r'(?:urgency|priority)=([^ ]+)')

from sourcerer.deb.version import Version

def parse_first_line(line):
    # SRCPKGNAME (VERSION).*((urgency|priority)=\S+)?
    if not first_re.match(line):
        raise ValueError, line
    srcpkg = line[:line.find(" ")]
    version = line[line.find("(")+1:line.find(")")]
    priority = "low"
    if prio_re.match(line):
        priority = prio_re.group(0).lower()

    return (srcpkg, version, priority)


def parse_last_line(line):
    maint = line[:line.find(">")+1].strip()
    date = line[line.find(">")+1:].strip()
    return (maint,date)
    

def parse_changelog_stanza(firstline, stanza, lastline):
    srcpkg, version, priority = parse_first_line(firstline)
    maint, date = parse_last_line(lastline)

    return {
        "package": srcpkg.lower(),
        "version": version.lower(),
        # forgot to take my medicine
        "urgency": priority.lower(),
        "maintainer": maint,
        "date": date,
        "changes": "".join(stanza).strip("\n")
    }


def parse_changelog(changelines):
    state = 0
    firstline = ""
    stanza = []
    rets = []
   
    for line in changelines:
        #print line[:-1]
        if state == 0:
            if (line.startswith(" ") or line.startswith("\t") or 
                not line.rstrip()):
                #print "State0 skip"
                continue
            try:
                (p,ver,pp) = parse_first_line(line.strip())
                Version(ver)
            except:
                stanza.append(line)
                #print "state0 Exception skip"
                continue
            firstline = line.strip()
            stanza = [line, '\n']
            state = 1
            continue

        if state == 1:
            stanza.append(line)

            if line.startswith(" --") and "@" in line:
                #print "state1 accept"
                # Last line of stanza
                rets.append(parse_changelog_stanza(firstline,
                                                   stanza,
                                                   line.strip()[3:]))
                state = 0

    # leftovers with no close line
    if state == 1:
        rets[-1]["changes"] += firstline
        if len(rets):
            rets[-1]["changes"] += "".join(stanza).strip("\n")

    return rets


if __name__ == '__main__':
    import pprint
    pprint.pprint(parse_changelog(file(sys.argv[1],"r")))
    
