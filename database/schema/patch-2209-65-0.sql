-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE product
    ADD COLUMN vcs integer;

ALTER TABLE distribution
    ADD COLUMN vcs integer;

COMMENT ON COLUMN product.vcs IS 'An enumeration specifying the default version control system for this project.';

COMMENT ON COLUMN distribution.vcs IS 'An enumeration specifying the default version control system for this distribution.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 65, 0);
