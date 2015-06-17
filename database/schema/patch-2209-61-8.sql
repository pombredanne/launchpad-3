-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Target and owner-target listings.
CREATE INDEX gitrepository__project__date_last_modified__idx
    ON gitrepository (project, date_last_modified)
    WHERE project IS NOT NULL;

CREATE INDEX gitrepository__distribution__spn__date_last_modified__idx
    ON gitrepository (distribution, sourcepackagename, date_last_modified)
    WHERE distribution IS NOT NULL;
    
CREATE INDEX gitrepository__owner__project__date_last_modified__idx
    ON gitrepository (owner, project, date_last_modified)
    WHERE project IS NOT NULL;

CREATE INDEX gitrepository__owner__distribution__spn__date_last_modified__idx
    ON gitrepository (
        owner, distribution, sourcepackagename, date_last_modified)
    WHERE distribution IS NOT NULL;


-- Owner listings.
CREATE INDEX gitrepository__owner__date_last_modified__idx
    ON gitrepository (owner, date_last_modified);


-- Target and owner-target default lookups.
CREATE INDEX gitrepository__project__target_default__idx
    ON gitrepository (project)
    WHERE target_default;
    
CREATE INDEX gitrepository__distribution__spn__target_default__idx
    ON gitrepository (distribution, sourcepackagename)
    WHERE target_default;
    
CREATE INDEX gitrepository__owner__project__owner_default__idx
    ON gitrepository (owner, project)
    WHERE owner_default;
    
CREATE INDEX gitrepository__owner__distribution__spn__owner_default__idx
    ON gitrepository (owner, distribution, sourcepackagename)
    WHERE owner_default;
    

-- FKs.
CREATE INDEX gitrepository__registrant__idx ON gitrepository (registrant);
CREATE INDEX gitrepository__reviewer__idx ON gitrepository (reviewer);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 61, 8);
