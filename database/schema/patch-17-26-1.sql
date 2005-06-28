SET client_min_messages=ERROR;

/* Don't allow multiple identical requests in the POExportRequest queue */
create unique index poexportrequest_person_key ON POExportRequest(person,potemplate,(coalesce(pofile,-1)));

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 26, 1);

