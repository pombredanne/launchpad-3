Page tests
==========

Page tests are doctests used to test Launchpad's frontend, primarily
using the zope testbrowser infrastructure.  All *.txt files found in
subdirectories of lib/canonical/launchpad/pagetests are run as page
tests, either independently or as part of a story.

Page tests whose names begin with a number (e.g. 42-foo.txt) will be
run together with other numbered page tests in the same directory as a
story.  This means that the database and librarian will not be reset
until all the tests in the story have been run, allowing them to
depend on state from previous tests in the story.

Unnumbered page tests (e.g. xx-bar.txt) in any subdirectory are run
independently, with a database and librarian reset after each.


Running page tests
==================

The page tests are run as part of the 'make check' to run all tests.

You can run a single story by doing:

  ./test.py -vv --test=pagetests/$dirname

This will run both the unnumbered tests in that directory and the
numbered page tests.

Unnumbered page tests can be run individually with:

  ./test.py -vv --test=xx-foo.txt

e.g.

  ./test.py -vv --test=xx-bug-index.txt

A post-mortem debugger is available, which stops right after your first
test error:

  ./test.py -Dvv --test=xx-bug-index.txt

You can also run tests inside specified subdirectories by using dotted
paths:

  ./test.py -vv . pagetests.rosetta
  ./test.py -vv . pagetests.rosetta.xx-translation-credits
  ./test.py -vv . doc.teammembership

If you run with -vvv you also get timings output at the end of the test
suite.

Footnotes
=========

There are a number of preconfigured testbrowser instances provided
that can make the intent of a test more obvious:

anon_browser:
    Use this instance to test behaviour of pages when not logged in.
user_browser:
    Use this instance to test behaviour of pages when logged in as an
    ordinary user.
admin_browser:
    Use this instance to test behaviour of pages when logged in as a
    Launchpad administrator.

If you are testing behaviour of a page when logged in as a specific
user, use the "browser" instance and configure the authentication for
that particular user.  Do not depend on the particular user account
the above browser objects log in as for these tests.

You can use the following authorization lines:

  for Foo Bar (an admin user):
    >>> browser = setupBrowser(auth='Basic foo.bar@canonical.com:test')

  for Sample Person (a normal user):
    >>> browser = setupBrowser(auth='Basic test@canonical.com:test')

  for No Privileges Person (a normal user who is not the owner of anything):
    >>> browser = setupBrowser(auth="Basic no-priv@canonical.com:test")

  for No Team Memberships (a person who is a member of NO teams):
    >>> browser = setupBrowser(auth="Basic no-team-memberships@test.com:test")

  for One Team Membership (a person who is a member of only one team, the
                           simple-team which has no special privileges):
    >>> browser = setupBrowser(auth="Basic one-membership@test.com:test")

  for Mark Shuttleworth: (launchpad admin, registry admin, mirror admin,
                          ubuntu team, testing spanish team)
    >>> browser = setupBrowser(auth='Basic mark@example.com:test')

  for Carlos: (launchpad admin, rosetta admin, ubuntu translators, testing
               spanish team)
    >>> browser = setupBrowser(auth='Basic carlos@canonical.com:test')

  for Salgado: (launchpad admin)
    >>> browser = setupBrowser(auth='Basic salgado@ubuntu.com:zeca')

  for Daf: (launchpad admin, rosetta admin)
    >>> browser = setupBrowser(auth='Basic daf@canonical.com:daf')

  for Jblack: (launchpad admins)
    >>> browser = setupBrowser(
    ...     auth='Basic james.blackwell@ubuntulinux.com:jblack')

  for Jdub: (ubuntu team)
    >>> browser = setupBrowser(auth='Basic jeff.waugh@ubuntulinux.com:jdub')

  for Cprov (ubuntu team and launchpad-buildd-admin)
    >>> browser = setupBrowser(
    ...     auth='Basic celso.providelo@canonical.com:cprov')

  for David Allouche (member of vcs-imports)
    >>> browser = setupBrowser(auth='Basic david.allouche@canonical.com:test')

  for Brad Crittenden (member of commercial-approvers)
    >>> browser = setupBrowser(auth='Basic bac@canonical.com:test')

  for Commercial Member (member of commercial-admins)
    >>> browser = setupBrowser(
    ...     auth='Basic commercial-member@canonical.com:test')
