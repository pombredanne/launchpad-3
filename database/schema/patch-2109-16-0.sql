-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE RequestedCDs
    ADD CONSTRAINT requestedcds__ds__arch__flav__request__key
    UNIQUE (distroseries, architecture, flavour, request);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 16, 0);
