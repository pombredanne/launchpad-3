SET client_min_messages=ERROR;

/* PersonTransferJob can handle jobs adding a member to a team
 * or merging to person objects.
 */
CREATE TABLE PersonTransferJob (
    id           SERIAL PRIMARY KEY,
    job          INTEGER NOT NULL UNIQUE REFERENCES Job(id),
    job_type     INTEGER NOT NULL,
    minor_person INTEGER NOT NULL REFERENCES Person(id),
    major_person INTEGER NOT NULL REFERENCES Person(id),
    json_data    text
);


INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
