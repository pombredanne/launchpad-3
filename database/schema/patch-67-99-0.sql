SET client_min_messages=ERROR;

/* XXX: Stuart, please add necessary indexes and a constraint on 'tag',
 *      it should be lowercase only and shouldn't contain any whitespace.
 */

CREATE TABLE BugTag (
    id SERIAL PRIMARY KEY,
    bug INTEGER NOT NULL,
    tag TEXT NOT NULL);


INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 0);
