SET client_min_messages=ERROR;

-- Branches must have distinct (or NULL) URL, so we can uniquely identify a
-- branch from a URL.

ALTER TABLE Branch ADD CONSTRAINT branch_url_unique UNIQUE(url);

-- Branch URLs are "normalised" by trimming all trailing slash characters. We
-- also add a constraint to prevent the introduction of trailing slashes. This
-- is needed to allow uniquely identifying a branch from a URL regardless of
-- trailing slashes.

UPDATE Branch SET url = trim(trailing '/' FROM url) WHERE url IS NOT NULL;

ALTER TABLE Branch ADD CONSTRAINT branch_url_no_trailing_slash
   CHECK (url NOT LIKE '%/');

-- Since we need to uniquely identify a branch by pull URL _or_ Supermirror
-- URL, we need to ensure that no pull URL looks like a Supermirror URL. That
-- would not be useful anyway.

ALTER TABLE Branch ADD CONSTRAINT branch_url_not_supermirror
   CHECK (url NOT LIKE 'http://bazaar.launchpad.net/%');


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 36, 0);
