-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX accesspolicygrant__grantee__policy__idx
    ON accesspolicygrant (grantee, policy);
CREATE INDEX accesspolicygrant__grantor__idx
    ON accesspolicygrant (grantor);

CREATE INDEX accessartifactgrant__grantee__artifact__idx
    ON accessartifactgrant (grantee, artifact);
CREATE INDEX accessartifactgrant__grantor__idx
    ON accessartifactgrant (grantor);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 23, 2);
