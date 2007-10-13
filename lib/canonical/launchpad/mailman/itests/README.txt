This directory contains integration tests for proper interaction between
Launchpad and Mailman.  These are /not/ unit tests that can be run inside of
either application though, so this directory is not a Python package.

In order to perform these integration tests, you must build Launchpad, enable
the build of Mailman in your launchpad.conf, and run 'make schema' and then
'make mailman_instance'.  Then you must start Launchpad with 'make run_all'.
This should also start the Mailman queue runners (look at your stdout
carefully).

Then, from the top of your Launchpad tree run this:

% lib/canonical/launchpad/mailman/itests/runtests.py

You should see all the numbered integration tests run in order, with no
failures.

You might also want a +mail-configure.zcml in your override-includes.

You should set the 'smtp' variable in the <mailman> section to
'localhost:9025'.  Note that you may need to set the LPCONFIG environment
variable to get the correct configuration file.
