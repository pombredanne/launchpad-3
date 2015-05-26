-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE GitRepository ADD COLUMN default_branch text;

COMMENT ON COLUMN GitRepository.default_branch IS 'The reference path of this repository''s default branch, or "HEAD".';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 61, 7);
