/* Expire unwanted sessions from the session database.

While the session machinery automatically removes expired sessions,
it does not do so particularly intelligently; it does not make decisions
based on the content of the session.

At the time of writing, we maintain sessions for 60 days and are getting
nearly half a million new sessions each day. If we expire sessions of
users who are not logged in after 1 day, we will reduce our 24 million
sessions down to a more managable 700,000.

*/

DELETE FROM SessionData
WHERE last_accessed < CURRENT_TIMESTAMP - '1 day'::interval
    AND client_id NOT IN (
        SELECT client_id FROM SessionPkgData
        WHERE product_id='launchpad.authenticateduser' AND key='logintime'
    );

