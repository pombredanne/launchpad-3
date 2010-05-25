SET client_min_messages=ERROR;

CREATE OR REPLACE FUNCTION calculate_bug_heat(bug_id integer)  RETURNS integer
LANGUAGE plpythonu AS $$
    from datetime import datetime

    class BugHeatConstants:
        PRIVACY = 150
        SECURITY = 250
        DUPLICATE = 6
        AFFECTED_USER = 4
        SUBSCRIBER = 2

    bug_data = plpy.execute("""
        SELECT * FROM Bug WHERE id = %s""" % bug_id)

    if bug_data.nrows() == 0:
        return 0

    bug = bug_data[0]
    if bug['duplicateof'] is not None:
        return 0

    heat = {}
    heat['privacy'] = 0
    heat['security'] = 0
    heat['dupes'] = (
        BugHeatConstants.DUPLICATE * bug['number_of_duplicates'])
    heat['affected_users'] = (
        BugHeatConstants.AFFECTED_USER *
        bug['users_affected_count'])

    if bug['private']:
        heat['privacy'] = BugHeatConstants.PRIVACY
    if bug['security_related']:
        heat['security'] = BugHeatConstants.SECURITY

    # Get the heat from subscribers.
    sub_count = plpy.execute("""
        SELECT bug, COUNT(id) AS sub_count
            FROM BugSubscription
            WHERE bug = %s
            GROUP BY bug
            """ % bug_id)

    if sub_count.nrows() > 0:
        heat['subscribers'] = (
            BugHeatConstants.SUBSCRIBER * sub_count[0]['sub_count'])

    # Get the heat from subscribers via duplicates.
    subs_from_dupes = plpy.execute("""
        SELECT bug.duplicateof AS dupe_of,
                COUNT(bugsubscription.id) AS dupe_sub_count
        FROM bugsubscription, bug
        WHERE   bug.duplicateof = %s
            AND Bugsubscription.bug = bug.id
        GROUP BY Bug.duplicateof""" % bug_id)
    if subs_from_dupes.nrows() > 0:
        heat['subcribers_from_dupes'] = (
            BugHeatConstants.SUBSCRIBER * sub_count[0]['dupe_sub_count'])

    total_heat = sum(heat.values())

    # Bugs decay over time. Every day the bug isn't touched its heat
    # decreases by 1%.
    pg_datetime_fmt = "%Y-%m-%d %H:%M:%S.%f"
    date_last_updated = datetime.strptime(
        bug['date_last_updated'], pg_datetime_fmt)
    days_since_last_update = (datetime.utcnow() - date_last_updated).days
    total_heat = int(total_heat * (0.99 ** days_since_last_update))

#    if days_since_last_update > 0:
#        # Bug heat increases by a quarter of the maximum bug heat
#        # divided by the number of days since the bug's creation date.
#        date_created = datetime.strptime(
#            bug['date_created'], pg_datetime_fmt)
#        date_last_message = datetime.strptime(
#            bug['date_last_message'], pg_datetime_fmt)
#        days_since_last_activity = (
#            datetime.utcnow() -
#            max(date_last_updated, date_last_message)).days
#        days_since_created = (datetime.utcnow() - date_created).days
#        max_heat = max(
#            task.target.max_bug_heat for task in self.bug.bugtasks)
#        if max_heat is not None and days_since_created > 0:
#            total_heat = total_heat + (max_heat * 0.25 / days_since_created)

    return total_heat
$$;

-- INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
