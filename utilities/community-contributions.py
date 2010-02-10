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
  -q            Print no non-essential messages.
  -h, --help    Print this help.
  --dry-run     Don't update the wiki, just print the new wiki page to stdout.
  --draft-run   Update the wiki "/Draft" page instead of the real page.
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
    sys.stderr.write("""ERROR: Unable to import from 'editmoin'. How to solve:
Get editmoin.py from launchpadlib's "contrib/" directory:

  http://bazaar.launchpad.net/~lazr-developers/launchpadlib/trunk/annotate/head%3A/contrib/editmoin.py

(Put it in the same directory as this script and everything should work.)
""")
    sys.exit(1)


# The output contains two classes of contributors: people who don't
# work for Canonical at all, and people who do work for Canonical but
# not on the Launchpad team.
#
# XXX: Karl Fogel 2009-09-10 bug=513608: We should use launchpadlib
# to consult Launchpad itself to find out who's a Canonical developer,
# and within that who's a Launchpad developer.

# People on the Canonical Launchpad team.
known_canonical_lp_devs = \
    [x.encode('utf-8', 'xmlcharrefreplace') \
         for x in (u'Aaron Bentley',
                   u'Abel Deuring',
                   u'Andrew Bennetts',
                   u'Barry Warsaw',
                   u'Bjorn Tillenius',
                   u'Björn Tillenius',
                   u'Brad Crittenden',
                   u'Brian Fromme',
                   u'Carlos Perello Marin',
                   u'Carlos Perelló Marín',
                   u'Celso Providelo',
                   u'Christian Reis',
                   u'kiko {_AT_} beetle',
                   u'Cody Somerville',
                   u'Cody A.W. Somerville',
                   u'Curtis Hovey',
                   u'Dafydd Harries',
                   u'Danilo Šegan',
                   u'Данило Шеган',
                   u'данило шеган',
                   u'Daniel Silverstone',
                   u'David Allouche',
                   u'David Murphy',
                   u'Deryck Hodge',
                   u'Diogo Matsubara',
                   u'Edwin Grubbs',
                   u'Elliot Murphy',
                   u'Francis Lacoste',
                   u'Francis J. Lacoste',
                   u'Gary Poster',
                   u'Gavin Panella',
                   u'Graham Binns',
                   u'Guilherme Salgado',
                   u'Henning Eggers',
                   u'James Henstridge',
                   u'Jelmer Vernooij',
                   u'Jeroen Vermeulen',
                   u'Jeroen T. Vermeulen',
                   u'Joey Stanford',
                   u'John Lenton',
                   u'Jonathan Lange',
                   u'jml {_AT_} canonical.com',
                   u'jml {_AT_} mumak.net',
                   u'Julian Edwards',
                   u'Karl Fogel',
                   u'Launchpad APA',
                   u'Launchpad Patch Queue Manager',
                   u'Launchpad PQM Bot',
                   u'Leonard Richardson',
                   u'Malcolm Cleaton',
                   u'Maris Fogels',
                   u'Mark Shuttleworth',
                   u'Martin Albisetti',
                   u'Martin Pool',
                   u'Matt Zimmerman',
                   u'Matthew Paul Thomas',
                   u'Matthew Revell',
                   u'matthew.revell {_AT_} canonical.com',
                   u'Michael Casadevall',
                   u'Michael Hudson',
                   u'Michael Nelson',
                   u'Muharem Hrnjadovic',
                   u'muharem {_AT_} canonical.com',
                   u'Paul Hummer',
                   u'Robert Collins',
                   u'Sidnei da Silva',
                   u'Stuart Bishop',
                   u'Steve McInerney',
                   u'<steve {_AT_} stedee.id.au>',
                   u'Tom Haddon',
                   u'Tim Penhey',
                   u'Tom Berger',
                   u'Ursula Junque',
                   )]

# People known to work for Canonical but not on the Launchpad team.
# Anyone with "@canonical.com" in their email address is considered to
# work for Canonical, but some people occasionally submit changes from
# their personal email addresses; this list contains people known to
# do that, so we can treat them appropriately in the output.
known_canonical_non_lp_devs = \
    [x.encode('utf-8', 'xmlcharrefreplace') \
         for x in (u'Adam Conrad',
                   u'Andrew Bennetts',
                   u'Anthony Lenton',
                   u'Cody Somerville',
                   u'Elliot Murphy',
                   u'Gabriel Neuman gneuman {_AT_} async.com',
                   u'Gustavo Niemeyer',
                   u'James Henstridge',
                   u'Jonathan Knowles',
                   u'Kees Cook',
                   u'LaMont Jones',
                   u'Martin Pool',
                   u'Matt Zimmerman',
                   u'Steve Kowalik',
                   )]

# Some people have made commits using various names and/or email 
# addresses, so this map will be used to merge them accordingly.
# The map is initialized from this list of pairs, where each pair is
# of the form (CONTRIBUTOR_AS_SEEN, UNIFYING_IDENTITY_FOR_CONTRIBUTOR).
merge_names_pairs = (
    (u'Jamal Fanaian <jfanaian {_AT_} gmail.com>',
     u'Jamal Fanaian <jamal.fanaian {_AT_} gmail.com>'),
    (u'Jamal Fanaian <jamal {_AT_} jfvm1>',
     u'Jamal Fanaian <jamal.fanaian {_AT_} gmail.com>'),
    (u'LaMont Jones <lamont {_AT_} rover3>',
     u'LaMont Jones <lamont {_AT_} debian.org>'),
    )
# Then put it in dictionary form with the correct encodings.
merge_names_map = { }
for pair in merge_names_pairs:
    merge_names_map[pair[0].encode('utf-8', 'xmlcharrefreplace')] = \
        pair[1].encode('utf-8', 'xmlcharrefreplace')


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
        # http://bazaar.launchpad.net/~launchpad-pqm/launchpad/devel/\
        # revision/launchpad@pqm.canonical.com-20090821221206-\
        # ritpv21q8w61gbpt
        #
        # In our links, even when the link text is a revnum, we still
        # use a rev-id for the target.  This is both so that the URL will
        # still work if you manually tweak it (say to "db-devel" from
        # "devel") and so that hovering over a revnum on the wiki page
        # will give you some information about it before you click
        # (because a rev id often identifies the committer).
        rev_id_url = rev_url_base + rev_id

        if len(self.contained_revs) <= 10:
            commits_block = "\n ".join(
                ["[[%s|%s]]" % (rev_url_base + lr.rev.revision_id, lr.revno)
                 for lr in self.contained_revs])
        else:
            commits_block = "''see the [[%s|full revision]] for details " \
                "(it contains %d commits)''" \
                % (rev_id_url, len(self.contained_revs))

        text = [
            " * [[%s|r%s]] -- %s\n" % (rev_id_url, self.top_rev.revno,
                                       date_str),
            " {{{\n%s\n}}}\n" % message,
            " '''Commits:'''\n ",
            commits_block,
            "\n",
            ]
        return ''.join(text)
  
  
# "ExternalContributor" is too much to type, so I guess we'll just use this.
class ExCon():
    """A contributor to Launchpad from outside Canonical's Launchpad team."""

    def __init__(self, name, is_canonical=False):
        """Create a new external contributor named NAME.
        If IS_CANONICAL is True, then this is a contributor from
        within Canonical, but not on the Launchpad team at Canonical.
        NAME is something like "Veronica Random <vr {_AT_} example.com>"."""
        self.name = name
        self.is_canonical = is_canonical
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
        name = self.name
        if self.is_canonical:
            name = name + " (Canonical developer)"
        if self.num_landings() == 1:
            plural = ""
        text = [
            "=== %s ===\n\n" % name,
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

    # If a contributor's address contains this, then they are a
    # Canonical developer -- maybe on the Launchpad team, maybe not.
    #
    # (It'd be nice to have the equivalent of a C static variable, so
    # this doesn't have to get reinitialized on each entry.  We could
    # always abuse the fact that keyword parameters to functions are
    # evaluated only once, at function definition time... but that
    # hardly seems like playing by the Marquess of Queensberry Rules.)
    canonical_addr = \
        u" {_AT_} canonical.com".encode('utf-8', 'xmlcharrefreplace')

    ex_cons_this_rev = []
    for author in authors:
        known_canonical_lp_dev = False
        known_canonical_non_lp_dev = False
        # The authors we list in the source code have their addresses
        # disguised (since this source code is public).  We must
        # disguise the ones coming from the Bazaar logs in the same way,
        # so string matches will work.
        author = author.encode('utf-8', 'xmlcharrefreplace')
        author = author.replace("@", " {_AT_} ")
        for name_fragment in known_canonical_lp_devs:
            if name_fragment in author:
                known_canonical_lp_dev = True
                break
        if known_canonical_lp_dev:
            continue

        # Use the merge names map to merge contributions from the same
        # person using alternate names and/or emails.
        author = merge_names_map.get(author, author)

        if canonical_addr in author:
            known_canonical_non_lp_dev = True
        else:
            for name_fragment in known_canonical_non_lp_devs:
                if name_fragment in author:
                    known_canonical_non_lp_dev = True
                    break

        ### There's a variant of the Singleton pattern that could be
        ### used for this, whereby instantiating an ExCon object would
        ### just get back an existing object if such has already been
        ### instantiated for this name.  But that would make this code
        ### non-reentrant, and that's just not cool.
        if author in all_ex_cons:
            ec = all_ex_cons[author]
        else:
            ec = ExCon(author, is_canonical=known_canonical_non_lp_dev)
            all_ex_cons[author] = ec
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

    def _toc(self, contributors):
        toc_text = []
        for val in contributors:
            plural = "s"
            if val.num_landings() == 1:
                plural = ""
            toc_text.extend(" 1. [[#%s|%s]] ''(%d top-level landing%s)''\n"
                            % (val.name_as_anchor, val.name,
                               val.num_landings(), plural))
        return toc_text
      
    def result(self):
        "Return a moin-wiki-syntax string with TOC followed by contributions."

        # Divide contributors into non-Canonical and Canonical.
        non_canonical_contributors = [x for x in self.all_ex_cons.values()
                                      if not x.is_canonical]
        canonical_contributors = [x for x in self.all_ex_cons.values()
                                      if x.is_canonical]
        # Sort them.
        non_canonical_contributors = sorted(non_canonical_contributors,
                                            key=lambda x: x.num_landings(),
                                            reverse=True)
        canonical_contributors = sorted(canonical_contributors,
                                        key=lambda x: x.num_landings(),
                                        reverse=True)

        text = [
            "-----\n\n",
            "= Who =\n\n"
            "== Contributors (from outside Canonical) ==\n\n",
            ]
        text.extend(self._toc(non_canonical_contributors))
        text.extend([
            "== Contributors (from Canonical, but outside "
            "the Launchpad team) ==\n\n",
            ])
        text.extend(self._toc(canonical_contributors))
        text.extend(["\n-----\n\n",
                     "= What =\n\n",
                     "== Contributions (from outside Canonical) ==\n\n",
                     ])
        for val in non_canonical_contributors:
            text.extend("<<Anchor(%s)>>\n" % val.name_as_anchor)
            text.extend(val.show_contributions())
        text.extend(["== Contributions (from Canonical, but outside "
                     "the Launchpad team) ==\n\n",
                     ])
        for val in canonical_contributors:
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
developers not on the Launchpad team at Canonical.

It only lists changes that have landed in the Launchpad ''devel'' \
tree, so changes that land in ''db-devel'' first may take a while to \
show up (see the [[Trunk|trunk explanation]] for more).

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

    wiki_dest = "https://dev.launchpad.net/Contributions"

    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    try:
        opts, args = getopt.getopt(sys.argv[1:], '?hq',
                                   ['help', 'usage', 'dry-run', 'draft-run'])
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
        elif opt == '--draft-run':
            wiki_dest += "/Draft"

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
        editshortcut(wiki_dest, editfile_func=update_if_modified)
        if not quiet:
            print "Done updating wiki."
    else:
        print page_contents


if __name__ == '__main__':
    main()
