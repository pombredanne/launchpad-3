# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C
"""Common database access glue code.

Here you'll find the Interfaces and SQLObject classes that you can use
to talk to the database. In general:

  import canonical.launchpad.database

  canonical.launchpad.database.Project.select('name="gnome"')
  ... etc

"""

