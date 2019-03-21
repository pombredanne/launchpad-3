-- Copyright 2019 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Branch ADD COLUMN deletion_status integer;
ALTER TABLE GitRepository ADD COLUMN deletion_status integer;

COMMENT ON COLUMN Branch.deletion_status IS 'The deletion status of this branch.';
COMMENT ON COLUMN GitRepository.deletion_status IS 'The deletion status of this repository.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2210, 01, 0);
