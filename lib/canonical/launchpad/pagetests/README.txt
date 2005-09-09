Page tests
==========

Every subdirectory of this one is considered a 'story'. Each story
is run against a fresh database instance, so we can easily avoid tests
stomping on each other. A story might be a walkthrough of a particular use
case, or a collection of tests based around some theme.

In each story directory, all .txt files are run as "page tests".[1]

A page test is a doctest that tests pages of the launchpad application.

The tests are run in ASCII sort-order, lowest first.  Each .txt file should
be named starting with a two-digit number.  It doesn't matter if numbers
are the same for several tests.  Typical names are:

  10-set-up-example-project.txt
  10-add-example-user.txt
  20-browse-projects.txt
  60-browse-users.txt

The test runner will issue a warning if files are put into the story
directory that do not match the NN-text-stuff.txt pattern.

If your test does not depend on any other test, prefix it with "00".
Then, it will be run first.
If your test is not depended on by any other test, prefix it with "xx".
That way, it will not be run unnecessarily when you want to run individual
tests.

Running page tests
==================

The page tests are run as part of the 'make check' to run all tests.

You can run individual page tests using:

  ./pagetests 10-browse-projects.txt

This will run all pagetests with a prefix of 00 to 09, and then the pagetest
you specified.


Footnotes
=========

1. Including this file, README.txt.  It doesn't run any tests, but that
   is okay.

2. You can use the following authorization lines:

  for Foo Bar (an admin user):
  ... Authorization: Basic Zm9vLmJhckBjYW5vbmljYWwuY29tOnRlc3Q=

  for Sample Person (a normal user):
  ... Authorization: Basic dGVzdEBjYW5vbmljYWwuY29tOnRlc3Q=

  for Mark Shuttleworth:
  ... Authorization: Basic bWFya0BoYmQuY29tOnRlc3Q=

  for Carlos:
  ... Authorization: Basic Y2FybG9zQGNhbm9uaWNhbC5jb206dGVzdA==

  for Salgado:
  ... Authorization: Basic Z3VpbGhlcm1lLnNhbGdhZG9AY2Fub25pY2FsLmNvbTp6ZWNh

