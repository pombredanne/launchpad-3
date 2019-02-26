-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE PersonSettings ADD COLUMN require_strong_email_authentication boolean;

COMMENT ON COLUMN PersonSettings.require_strong_email_authentication IS 'Require strong authentication for incoming emails.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 68, 2);
