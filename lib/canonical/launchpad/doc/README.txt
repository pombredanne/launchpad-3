This directory contains the Launchpad system documentation. The intent is for
the documentation found in this directory to:

- describe various aspects of the Launchpad system: adapters, utilities, event
  handlers and other things of interest to people that want to make things work
  in Launchpad

- be executable, and test the code that it documents, i.e. doctests

- These tests should not contain tests that reduce the documents worth as
  documentation. Boiler plate should be factored out into setUp and
  tearDown routines in test_system_documentation.py. Common imports or
  useful globals are installed by setGlobs() in
  test_system_documentation.py

