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


    def get_max_heat_for_bug(bug_id):
        bug_tasks = plpy.execute(
            "SELECT * FROM BugTask WHERE bug = %s" % bug_id)

        max_heats = []
        for bug_task in bug_tasks:
            if bug_task['product'] is not None:
                product = plpy.execute(
                    "SELECT max_bug_heat FROM Product WHERE id = %s" %
                    bug_task['product'])[0]
                max_heats.append(product['max_bug_heat'])
            elif bug_task['distribution']:
                distribution = plpy.execute(
                    "SELECT max_bug_heat FROM Distribution WHERE id = %s" %
                    bug_task['distribution'])[0]
                max_heats.append(distribution['max_bug_heat'])
            elif bug_task['productseries'] is not None:
                product_series = plpy.execute("""
                    SELECT Product.max_bug_heat
                      FROM ProductSeries, Product
                     WHERE ProductSeries.Product = Product.id
                       AND ProductSeries.id = %s"""%
                    bug_task['productseries'])[0]
                max_heats.append(product_series['max_bug_heat'])
            elif bug_task['distroseries']:
                distro_series = plpy.execute("""
                    SELECT Distribution.max_bug_heat
                      FROM DistroSeries, Distribution
                     WHERE DistroSeries.Distribution = Distribution.id
                       AND DistroSeries.id = %s"""%
                    bug_task['distroseries'])[0]
                max_heats.append(distro_series['max_bug_heat'])
            else:
                pass

        return max(max_heats)


    # It would be nice to be able to just SELECT * here, but we need to
    # format the timestamps so that datetime.strptime() won't choke on
    # them.
    bug_data = plpy.execute("""
        SELECT
            duplicateof,
            private,
            security_related,
            number_of_duplicates,
            users_affected_count,
            TO_CHAR(datecreated, '%(date_format)s')
                AS formatted_date_created,
            TO_CHAR(date_last_updated, '%(date_format)s')
                AS formatted_date_last_updated,
            TO_CHAR(date_last_message, '%(date_format)s')
                AS formatted_date_last_message
        FROM Bug WHERE id = %(bug_id)s""" % {
            'bug_id': bug_id,
            'date_format': 'YYYY-MM-DD HH24:MI:SS',
            })

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
    pg_datetime_fmt = "%Y-%m-%d %H:%M:%S"
    date_last_updated = datetime.strptime(
        bug['formatted_date_last_updated'], pg_datetime_fmt)
    days_since_last_update = (datetime.utcnow() - date_last_updated).days
    total_heat = int(total_heat * (0.99 ** days_since_last_update))

    if days_since_last_update > 0:
        # Bug heat increases by a quarter of the maximum bug heat
        # divided by the number of days since the bug's creation date.
        date_created = datetime.strptime(
            bug['formatted_date_created'], pg_datetime_fmt)

        if bug['formatted_date_last_message'] is not None:
            date_last_message = datetime.strptime(
                bug['formatted_date_last_message'], pg_datetime_fmt)
            oldest_date = max(date_last_updated, date_last_message)
        else:
            date_last_message = None
            oldest_date = date_last_updated

        days_since_last_activity = (datetime.utcnow() - oldest_date).days
        days_since_created = (datetime.utcnow() - date_created).days
        max_heat = get_max_heat_for_bug(bug_id)
        if max_heat is not None and days_since_created > 0:
            return total_heat + (max_heat * 0.25 / days_since_created)

    return total_heat
$$;

-- INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
