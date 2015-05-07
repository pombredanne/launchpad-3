-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE product
    ADD COLUMN vcs_default integer;

COMMENT ON COLUMN product.vcs_default IS 'An enumeration specifying the default version control system for this product/project.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 65, 0);
