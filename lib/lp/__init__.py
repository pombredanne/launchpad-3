# Copyright 2006-2009 Canonical Ltd.  All rights reserved.
"""The lp namespace package.

WARNING: This is a namespace package, it should only include other packages,
but no actual code or modules.

This is the root of the Launchpad application namespace.

You'll find in this package:

    - Application packages:
        lp.answers
        lp.bugs
        lp.code
        etc.

   - lp.registry The package containing the core content on which all other
     apps build.

   - lp.coop The app-collaboration namespace package

   - lp.services The namespace package for all general services.

   - lp.app The package that integrates all into the web application known as
     launchpad.net

   - lp.testing General Launchpad testing infrastructure.

The Launchpad code should be structured like an onion, where each layers can
only know about and use (and thus import) from the layers above it).

Here are these layers:

    - General Library code (Python stdlib, storm, zope, twisted, bzr, etc.)
    - Lazr Library code (lazr.*)
    - lp.services
    - lp.registry
    - lp applications (lp.answers, lp.bugs, ...)
    - lp.coop
    - lp.app
"""
