-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE translationtemplateitem
    ADD COLUMN msgid_singular integer REFERENCES pomsgid,
    ADD COLUMN msgid_plural integer REFERENCES pomsgid;
ALTER TABLE potemplate ADD COLUMN suggestive bool;
ALTER TABLE potmsgset ADD COLUMN suggestive bool;
ALTER TABLE translationmessage
    ADD COLUMN msgid_singular integer REFERENCES pomsgid,
    ADD COLUMN msgid_plural integer REFERENCES pomsgid,
    ADD COLUMN suggestive bool;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 62, 1);
