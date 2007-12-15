This directory contains integration tests for proper interaction between
Launchpad and Mailman.  These are /not/ unit tests, and cannot be run inside
of either application though, so this directory is not a Python package.  See
also bug #158531 for changes that may fix this restriction.

Here are the steps to run these integration tests:

- Build and run Launchpad with the following command:

  make LPCONFIG=mailman-itests schema
  make LPCONFIG=mailman-itests mailman_instance
  make LPCONFIG=mailman-itests run_all

- In a separate shell, run the LP/MM integration tests:

  LPCONFIG=mailman-itests lib/canonical/launchpad/mailman/itests/runtests.py

- Sit back and marvel at Joseph and the Amazing Passing Tests.

NOTES:

- If you've done this before and possibly have old branches laying around, you
  will probably want to clean out and rebuild Mailman.  This may also be
  necessary if your var_dir is on a temporary file system and you've rebootted
  since the last time you ran the tests.  To clean everything out:

  % rm -rf /tmp/var/mailman (or whatever var_dir points to above)
  % rm -rf lib/mailman

  Then re-make mailman_instance as above.  If you don't remove lib/mailman,
  'make mailman_instance' will not do anything.
