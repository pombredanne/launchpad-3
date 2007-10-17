set client_min_messages=ERROR;

CREATE UNIQUE INDEX bugtask__date_closed__id__idx
    ON bugtask(date_closed,id) WHERE status=30;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 13, 1);

