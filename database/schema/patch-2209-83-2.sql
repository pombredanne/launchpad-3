-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Snap ADD COLUMN source_tarball boolean DEFAULT false NOT NULL;

COMMENT ON COLUMN Snap.source_tarball IS 'If true, builds of this snap should also build a tarball containing all source code, including external dependencies.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 83, 2);
