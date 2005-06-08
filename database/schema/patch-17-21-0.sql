
set client_min_messages=ERROR;

CREATE TABLE POExportRequest (
	id		serial PRIMARY KEY,
	person		integer
                            CONSTRAINT poexportrequest_person_fk
                            REFERENCES Person NOT NULL,
	potemplate	integer
                            CONSTRAINT poeportrequest_potemplate_fk
                            REFERENCES POTemplate NOT NULL,
	pofile		integer
                            CONSTRAINT poexportrequest_pofile_fk
                            REFERENCES POFile
);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 21, 0);

