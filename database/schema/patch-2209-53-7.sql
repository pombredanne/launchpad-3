-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE distribution
    ADD COLUMN official_packages boolean DEFAULT false NOT NULL,
    ADD COLUMN supports_ppas boolean DEFAULT false NOT NULL,
    ADD COLUMN supports_mirrors boolean DEFAULT false NOT NULL;
ALTER TABLE distroseriesparent
    ADD COLUMN inherit_overrides boolean DEFAULT false NOT NULL;
UPDATE distribution
    SET official_packages=true, supports_ppas=true, supports_mirrors=true
    WHERE name = 'ubuntu';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 53, 7);
