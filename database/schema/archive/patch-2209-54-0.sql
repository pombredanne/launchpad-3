-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE codereviewinlinecomment (
    previewdiff integer NOT NULL REFERENCES previewdiff,
    person integer NOT NULL REFERENCES person,
    comment integer PRIMARY KEY REFERENCES codereviewmessage,
    comments text NOT NULL
);

CREATE INDEX codereviewinlinecomment__person__idx ON
    codereviewinlinecomment(person);
CREATE INDEX codereviewinlinecomment__previewdiff__idx ON
    codereviewinlinecomment(previewdiff);

CREATE TABLE codereviewinlinecommentdraft (
    previewdiff integer NOT NULL REFERENCES previewdiff,
    person integer NOT NULL REFERENCES person,
    comments text NOT NULL,
    PRIMARY KEY (previewdiff, person)
);

CREATE INDEX codereviewinlinecommentdraft__person__idx ON
    codereviewinlinecommentdraft(person);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 54, 0);
