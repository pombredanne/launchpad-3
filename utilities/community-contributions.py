#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Show what Launchpad community contributors have done.

Trawl a Launchpad branch's history to detect contributions by non-Canonical
developers, then update https://dev.launchpad.net/Contributions accordingly.

Usage: community-contributions.py [options] PATH_TO_LAUNCHPAD_DEVEL_BRANCH

Requirements:
       You need a 'devel' branch of Launchpad available locally (see
       https://dev.launchpad.net/Getting), your ~/.moin_ids file must
       be set up correctly, and you need editmoin.py (if you don't
       have it, the error message will tell you where to get it).

Options:
  -q          Print no non-essential messages.
  -h, --help  Print this help.
  --dry-run   Don't update the wiki, just print the new wiki page to stdout.
"""

# General notes:
#
# The Right Way to do this would probably be to output some kind of
# XML format, and then have a separate converter script transform that
# to wiki syntax and update the wiki page.  But as the wiki is our
# only consumer right now, we just output wiki syntax and update the
# wiki page directly, premature generalization being the root of all
# evil.
#
# For understanding the code, you may find it helpful to see
# bzrlib/log.py and http://bazaar-vcs.org/Integrating_with_Bazaar.

import getopt
import re
import sys

from bzrlib import log
from bzrlib.branch import Branch
from bzrlib.osutils import format_date

try:
    from editmoin import editshortcut
except:
    sys.stderr.write("""ERROR: Unable to import from 'editmoin'.  How to solve:
Get editmoin.py from launchpadlib's "contrib/" directory:

  http://bazaar.launchpad.net/~lazr-developers/launchpadlib/trunk/annotate/head%3A/contrib/editmoin.py

(Put it in the same directory as this script and everything should work.)
""")
    sys.exit(1)


# While anyone with "@canonical.com" in their email address will be
# counted as a Canonical contributor, sometimes Canonical people
# submit from personal addresses, so we still need a list.
#
# XXX: Karl Fogel 2009-09-10: Really, this ought to use launchpadlib
# to consult Launchpad itself to find out who's a Canonical developer.
known_canonical_devs = (
    u'Aaron Bentley',
    u'Abel Deuring',
    u'Adam Conrad',
    u'Andrew Bennetts',
    u'Barry Warsaw',
    u'Brad Crittenden',
    u'Carlos Perello Marin',
    u'Carlos Perelló Marín',
    u'Celso Providelo',
    u'Christian Robottom Reis',
    u'Cody Somerville',
    u'Curtis Hovey',
    u'Dafydd Harries',
    u'Daniel Silverstone',
    u'Danilo Šegan',
    u'Данило Шеган',
    u'данило шеган',
    u'David Allouche',
    u'Deryck Hodge',
    u'Diogo Matsubara',
    u'Elliot Murphy',
    u'Francis J. Lacoste',
    u'Gabriel Neuman gneuman@async.com',
    u'Gary Poster',
    u'Guilherme Salgado',
    u'Gustavo Niemeyer',
    u'Henning Eggers',
    u'Herb McNew',
    u'James Henstridge',
    u'Jeroen Vermeulen',
    u'Jonathan Knowles',
    u'Jonathan Lange',
    u'Julian Edwards',
    u'Karl Fogel',
    u'Launch Pad',
    u'Launchpad Developers',
    u'Leonard Richardson',
    u'Malcolm Cleaton',
    u'Maris Fogels',
    u'Martin Albisetti',
    u'Matt Zimmerman',
    u'Matthew Revell',
    u'Michael Hudson',
    u'Michael Nelson',
    u'Muharem Hrnjadovic',
    u'Patch Queue Manager',
    u'Paul Hummer',
    u'Robert Collins',
    u'Sidnei',
    u'Sidnei da Silva',
    u'Steve McInerney',
    u'Stuart Bishop',
    u'Tom Berger',
    u'david',
    u'jml@mumak.net',
    u'kiko@beetle',
    )


class ContainerRevision():
    """A wrapper for a top-level LogRevision containing child LogRevisions."""

    def __init__(self, top_lr):
        self.top_rev = top_lr       # e.g. LogRevision for r9371.
        self.contained_revs = []    # e.g. [ {9369.1.1}, {9206.4.4}, ... ],
                                    # where "{X}" means "LogRevision for X"

    def add_subrev(self, lr):
        """Add a descendant child of this container revision."""
        self.contained_revs.append(lr)

    def __str__(self):
        timestamp = self.top_rev.rev.timestamp
        timezone = self.top_rev.rev.timezone
        message = self.top_rev.rev.message or "(NO LOG MESSAGE)"
        rev_id = self.top_rev.rev.revision_id or "(NO REVISION ID)"
        inventory_sha1 = self.top_rev.rev.inventory_sha1
        if timestamp:
            date_str = format_date(timestamp, timezone or 0, 'original')
        else:
            date_str = "(NO DATE)"

        # XXX: Karl Fogel 2009-09-10: just using 'devel' branch for
        # now.  We have four trunks; that makes life hard.  Not sure
        # what to do about that; unifying the data is possible, but a
        # bit of work.  See https://dev.launchpad.net/Trunk for more
        # information.
        rev_url_base = (
            "http://bazaar.launchpad.net/~launchpad-pqm/"
            "launchpad/devel/revision/")

        # In loggerhead, you can use either a revision number or a
        # revision ID.  In other words, these would reach the same page:
        #
        # http://bazaar.launchpad.net/~launchpad-pqm/launchpad/devel/\
        # revision/9202
        #
        #   -and-
        #
        # http://bazaar.launchpad.net/~launchpad-pqm/launchpad/devel/revision/\
        # launchpad@pqm.canonical.com-20090821221206-ritpv21q8w61gbpt
        #
        # In our links, even when the link text is a revnum, we still
        # use a rev-id for the target.  This is both so that the URL will
        # still work if you manually tweak it (say to "db-devel" from
        # "devel") and so that hovering over a revnum on the wiki page
        # will give you some information about it before you click
        # (because a rev id often identifies the committer).
        rev_id_url = rev_url_base + rev_id
        text = [
            " * [[%s|r%s]] -- %s\n" % (rev_id_url, self.top_rev.revno,
                                       date_str),
            " {{{\n%s\n}}}\n" % message,
            " '''Commits:'''\n ",
            "\n ".join(["[[%s|%s]]" % (rev_url_base + lr.rev.revision_id,
                                       lr.revno)
                        for lr in self.contained_revs]),
            "\n",
            ]
        return ''.join(text)
  
  
# "ExternalContributor" is too much to type, so I guess we'll just use this.
class ExCon():
    """A contributor to Launchpad from outside Canonical."""

    def __init__(self, name):
        """Create a new external contributor named NAME.  NAME is usually
        e.g. "Veronica Random <veronica@example.com>", but any "@"-sign
        will be disguised in the new object."""

        self.name = name.replace("@", " {_AT_} ")
        # If name is "Veronica Random <veronica {_AT_} example.com>",
        # then name_as_anchor will be "veronica_random".
        self.name_as_anchor = \
            re.compile("\\s+").sub("_", name.split("<")[0].strip()).lower()
        # All the top-level revisions this contributor is associated with
        # (key == value == ContainerRevision).  We use a dictionary
        # instead of list to get set semantics; set() would be overkill.
        self._landings = {}

    def num_landings(self):
        """Return the number of top-level landings that include revisions
        by this contributor."""
        return len(self._landings)

    def add_top_level_revision(self, cr):
        "Record ContainableRevision CR as associated with this contributor."
        self._landings[cr] = cr

    def show_contributions(self):
        "Return a wikified string showing this contributor's contributions."
        plural = "s"
        if self.num_landings() == 1:
            plural = ""
        text = [
            "== %s ==\n\n" % self.name,
            "''%d top-level landing%s:''\n\n" % (self.num_landings(), plural),
            ''.join(map(str, sorted(self._landings,
                                    key=lambda x: x.top_rev.revno,
                                    reverse=True))),
            "\n",
            ]
        return ''.join(text)


def get_ex_cons(authors, all_ex_cons):
    """Return a list of ExCon objects corresponding to AUTHORS (a list
    of strings).  If there are no external contributors in authors,
    return an empty list.

    ALL_EX_CONS is a dictionary mapping author names (as received from
    the bzr logs, i.e., with email address undisguised) to ExCon objects.
    """
    ex_cons_this_rev = []
    for a in authors:
        known = False
        for name_fragment in known_canonical_devs:
            if u"@canonical.com" in a or name_fragment in a:
                known = True
                break
        if not known:
            ### There's a variant of the Singleton pattern that could be
            ### used for this, whereby instantiating an ExCon object would
            ### just get back an existing object if such has already been
            ### instantiated for this name.  But that would make this code
            ### non-reentrant, and that's just not cool.
            if a in all_ex_cons:
                ec = all_ex_cons[a]
            else:
                ec = ExCon(a)
                all_ex_cons[a] = ec
            ex_cons_this_rev.append(ec)
    return ex_cons_this_rev


# The LogFormatter abstract class should really be called LogReceiver
# or something -- subclasses don't have to be about display.
class LogExCons(log.LogFormatter):
    """Log all the external contributions, by Contributor."""

    # See log.LogFormatter documentation.
    supports_merge_revisions = True

    def __init__(self):
        super(LogExCons, self).__init__(to_file=None)
        # Dictionary mapping author names (with undisguised email
        # addresses) to ExCon objects.
        self.all_ex_cons = {}
        # ContainerRevision object representing most-recently-seen
        # top-level rev.
        current_top_level_rev = None

    def result(self):
        "Return a moin-wiki-syntax string with TOC followed by contributions."
        text = [
            "-----\n\n",
            "= Who =\n\n",
            ]
        sorted_contributors = sorted(self.all_ex_cons.values(),
                                     key=lambda x: x.num_landings(),
                                     reverse=True)
        for val in sorted_contributors:
            plural = "s"
            if val.num_landings() == 1:
                plural = ""
            text.extend(" 1. [[#%s|%s]] ''(%d top-level landing%s)''\n"
                        % (val.name_as_anchor, val.name,
                           val.num_landings(), plural))
        text.extend(["\n-----\n\n",
                     "= What =\n\n",
                     ])
        for val in sorted_contributors:
            text.extend("<<Anchor(%s)>>\n" % val.name_as_anchor)
            text.extend(val.show_contributions())
        return ''.join(text)

    def log_revision(self, lr):
        """Log a revision.
        :param  lr:   The LogRevision to be logged.
        """
        # We count on always seeing the containing rev before its subrevs.
        if lr.merge_depth == 0:
            self.current_top_level_rev = ContainerRevision(lr)
        else:
            self.current_top_level_rev.add_subrev(lr)
        ex_cons = get_ex_cons(lr.rev.get_apparent_authors(), self.all_ex_cons)
        for ec in ex_cons:
            ec.add_top_level_revision(self.current_top_level_rev)


# XXX: Karl Fogel 2009-09-10: is this really necessary?  See bzrlib/log.py.
log.log_formatter_registry.register('external_contributors', LogExCons,
                                    'Find non-Canonical contributors.')


def usage():
    print __doc__


page_intro = """This page shows contributions to Launchpad from \
outside Canonical.  It only lists changes that have landed in the \
Launchpad ''devel'' tree, so changes that land in ''db-devel'' first \
may take a while to show up (see the [[Trunk|trunk explanation]] for \
more).

~-''Note for maintainers: this page is updated every 10 minutes by a \
cron job running as kfogel on devpad (though if there are no new \
contributions, the page's timestamp won't change).  The code that \
generates this page is \
[[http://bazaar.launchpad.net/%7Elaunchpad-pqm/launchpad/devel/annotate/head%3A/utilities/community-contributions.py|utilities/community-contributions.py]] \
in the Launchpad tree.''-~

"""

def main():
    quiet = False
    target = None
    dry_run = False

    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    try:
        opts, args = getopt.getopt(sys.argv[1:], '?hq',
                                   ['help', 'usage', 'dry-run'])
    except getopt.GetoptError, e:
        sys.stderr.write("ERROR: " + str(e) + '\n\n')
        usage()
        sys.exit(1)

    for opt, value in opts:
        if opt == '--help' or opt == '-h' or opt == '-?' or opt == 'usage':
            usage()
            sys.exit(0)
        elif opt == '-q' or opt == '--quiet':
            quiet = True
        elif opt == '--dry-run':
            dry_run = True

    # Ensure we have the arguments we need.
    if len(args) < 1:
        sys.stderr.write("ERROR: path to Launchpad branch "
                         "required as argument\n")
        usage()
        sys.exit(1)

    target = args[0]

    # Do everything.
    b = Branch.open(target)

    # XXX: Karl Fogel 2009-09-10: 8976 is the first non-Canonical
    # contribution on 'devel'.  On 'db-devel', the magic revision
    # number is 8327.  We're aiming at 'devel' right now, but perhaps
    # it would be good to parameterize this, or just auto-detect the
    # branch and choose the right number.
    logger = log.Logger(b, {'start_revision' : 8976,
                            'direction' : 'reverse',
                            'levels' : 0, })
    lec = LogExCons()
    if not quiet:
        print "Calculating (this may take a while)..."
    logger.show(lec)  # Won't "show" anything -- just gathers data.
    page_contents = page_intro + lec.result()
    def update_if_modified(moinfile):
        if moinfile._unescape(moinfile.body) == page_contents:
            return 0  # Nothing changed, so cancel the edit.
        else:
            moinfile.body = page_contents
            return 1
    if not dry_run:
        if not quiet:
            print "Updating wiki..."
        # Not sure how to get editmoin to obey our quiet flag.
        editshortcut("https://dev.launchpad.net/Contributions",
                     editfile_func=update_if_modified)
        if not quiet:
            print "Done updating wiki."
    else:
        print page_contents


if __name__ == '__main__':
    main()
