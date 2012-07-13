-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Add new columns to replace Product.private_bugs and BranchVisibilityPolicy.
ALTER TABLE product ADD COLUMN branch_information_type_policy integer;
ALTER TABLE product ADD COLUMN bug_information_type_policy integer;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 26, 0);
