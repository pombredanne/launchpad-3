-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Snap privacy model is based only on ownership, similarly to Archives.
ALTER TABLE Snap ADD COLUMN private boolean DEFAULT false NOT NULL;

COMMENT ON COLUMN Snap.private IS 'Whether or not this snap is private.';


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 1);
