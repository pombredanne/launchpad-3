# Copyright 2006-2009 Canonical Ltd.  All rights reserved.
"""The lp.coop namespace package.

WARNING: This is a namespace package, it should only include other packages,
but no actual code or modules.

In this namespace live packages that bridges the different Launchpad
applications together.

For example, lp.coop.answersbugs contains the code handling linking answers
and bugs together.

Packages in this namespace can depends on any of the Launchpad applications.
The only thing they can't import from is lp.app.
"""
