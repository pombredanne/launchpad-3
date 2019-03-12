-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Archive ADD COLUMN dirty_suites text;

COMMENT ON COLUMN Archive.dirty_suites IS 'A JSON-encoded list of suites in this archive that should be considered dirty on the next publisher run regardless of publications.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 71, 1);
