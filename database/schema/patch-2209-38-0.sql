-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX creator__dateuploaded__id__idx ON sourcepackagerelease USING btree (creator, dateuploaded DESC, id) WHERE (dateuploaded IS NOT NULL);

CREATE INDEX maintainer__dateuploaded__id__idx ON sourcepackagerelease USING btree (maintainer, dateuploaded DESC, id) WHERE (dateuploaded IS NOT NULL);

CREATE INDEX dateuploaded__id__idx ON sourcepackagerelease USING btree (dateuploaded DESC, id) WHERE (dateuploaded IS NOT NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 38, 0);
