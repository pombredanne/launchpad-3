/* Copyright 2014 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.app.date', function(Y) {

var namespace = Y.namespace('lp.app.date');

namespace.parse_date = function(str) {
    // Parse an ISO-8601 date
    var re = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|\+00:00)$/;
    // Milliseconds may be missing and are boring, so only take year to
    // seconds.
    var bits = re.exec(str).slice(1, 7).map(Number);
    // Adjusting for the fact that Date.UTC uses 0-11 for months
    bits[1] -= 1;
    return new Date(Date.UTC.apply(null, bits));
};

namespace.approximatedate = function(date) {
    // Display approximate time an event happened when it happened less than 1
    // day ago.
    var now = (new Date).valueOf();
    var timedelta = now - date;
    var unit = "";
    var prefix = "";
    var suffix = "";
    if (timedelta >= 0) {
        suffix = " ago";
    } else {
        prefix = "in ";
        timedelta = -timedelta;
    }
    var days = timedelta / 86400000;
    var hours = timedelta / 3600000;
    var minutes = timedelta / 60000;
    var amount = 0;
    if (days > 1) {
        return 'on ' + Y.Date.format(
            new Date(date), {format: '%Y-%m-%d'});
    } else {
        if (hours >= 1) {
            amount = hours;
            unit = "hour";
        } else if (minutes >= 1) {
            amount = minutes;
            unit = "minute";
        } else {
            return prefix + "a moment" + suffix;
        }
        if (Math.floor(amount) > 1) {
            unit = unit + 's';
        }
        return prefix + Math.floor(amount) + ' ' + unit + suffix;
    }
};
}, "0.1", {'requires': ['datatype-date']});
