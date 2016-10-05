-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

DROP FUNCTION generate_openid_identifier();
DROP FUNCTION set_openid_identifier();
DROP FUNCTION set_shipit_normalized_address();
DROP FUNCTION is_printable_ascii(text);

-- Unused since r5499.
DROP FUNCTION is_team(integer);
DROP FUNCTION is_team(text);

-- Unused since r9019.
DROP VIEW potexport;

-- Unused since r18209.
DROP VIEW binarypackagefilepublishing;
DROP VIEW sourcepackagefilepublishing;

-- Unused since r17805.
DROP TABLE bugcve;
DROP TABLE questionbug;
DROP TABLE specificationbug;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 77, 3);
