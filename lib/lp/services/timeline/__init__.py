# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""lp.services.timeline provides a timeline for varied actions.

This is used as part of determining where time goes in a request.

NOTE that it is not LP's timeline-view for products, though they are similar in
intent and concept (If a better name presents itself, this package may be
renamed).

Because this is part of lp.services, packages in this namespace can only use
general LAZR or library functionality.
"""
