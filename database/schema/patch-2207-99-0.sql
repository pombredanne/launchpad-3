-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE product
    ADD COLUMN max_heat integer DEFAULT 0 NOT NULL;
ALTER TABLE distribution
    ADD COLUMN max_heat integer DEFAULT 0 NOT NULL;
ALTER TABLE distributionsourcepackage
    ADD COLUMN max_heat integer DEFAULT 0 NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
