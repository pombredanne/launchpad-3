This directory contains integration tests for proper interaction between
Launchpad and Mailman.  These are /not/ unit tests, and cannot be run inside
of either application though, so this directory is not a Python package.  See
also bug #158531 for changes that may fix this restriction.

Here are the steps to run these integration tests:

- Build and run Launchpad with the following command:

  make LPCONFIG=mailman-itests schema
  make LPCONFIG=mailman-itests run_all

- In a separate shell, run the LP/MM integration tests:

  LPCONFIG=mailman-itests lib/canonical/launchpad/mailman/itests/runtests.py

- Sit back and marvel at Joseph and the Amazing Passing Tests.

NOTES:

- If you've done this before and possibly have old branches laying around, you
  will probably want to clean out and rebuild Mailman.  This may also be
  necessary if your var_dir is on a temporary file system and you've rebootted
  since the last time you ran the tests.  To clean everything out:

  % make LPCONFIG=mailman-itests clean

  Then re-run the schema target again.

- Be sure that you have xmlrpc-private.launchpad.dev in your /etc/hosts file.
  This should point to the same IP address (127.0.0.88) as all your other
  *.dev vhosts.
