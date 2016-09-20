-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX question__datecreated__idx ON question(datecreated);
CREATE INDEX specification__datecreated__id__idx ON specification(datecreated, id DESC);
CREATE INDEX product__datecreated__id__idx ON product(datecreated, id DESC);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 67, 3);
