-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX archive__signing_key_fingerprint__idx
    ON archive(signing_key_fingerprint);
CREATE INDEX packageupload__signing_key_fingerprint__idx
    ON packageupload(signing_key_fingerprint);
CREATE INDEX revision__signing_key_fingerprint__idx
    ON revision(signing_key_fingerprint);
CREATE INDEX signedcodeofconduct__signing_key_fingerprint__idx
    ON signedcodeofconduct(signing_key_fingerprint);
CREATE INDEX sourcepackagerelease__signing_key_fingerprint__idx
    ON sourcepackagerelease(signing_key_fingerprint);

CREATE INDEX archive__signing_key_owner__idx
    ON archive(signing_key_owner);
CREATE INDEX packageupload__signing_key_owner__idx
    ON packageupload(signing_key_owner);
CREATE INDEX revision__signing_key_owner__idx
    ON revision(signing_key_owner);
CREATE INDEX sourcepackagerelease__signing_key_owner__idx
    ON sourcepackagerelease(signing_key_owner);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 99, 1);
