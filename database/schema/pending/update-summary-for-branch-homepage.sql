SET client_min_messages=ERROR;

-- Append the home page to the summary where both are set.
UPDATE Branch
SET summary = (summary || E'\n\n' || 'Home page: ' || home_page)
WHERE
    summary IS NOT NULL
AND home_page IS NOT NULL;

-- Set the home page to be the summary if the summary is not set.
UPDATE Branch
SET summary = 'Home page: ' || home_page
WHERE
    summary IS NULL
AND home_page IS NOT NULL;

-- Drop the column later as the horrible BranchWithSortKeys
-- view uses it.  I'm hoping to kill this view shortly.

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 28, 0);
