/* Copyright 2014 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.app.date', function(Y) {
    
var namespace = Y.namespace('lp.app.date');

namespace.parse_date = function(str) {
    // Adds the ability to parse ISO-8601 when it doesn't already exist.
    // Useful for Lucid testing. Adapted from http://goo.gl/m6pflw
    var parts = str.split('T'),
    dateParts = parts[0].split('-'),
    time = parts[1]
    var timeRegExp = new RegExp('Z');
    if (timeRegExp.test(time)) {
        timeParts = parts[1].split('Z')
    } else {
        timeParts = parts[1].split('+')
    }
    timeSubParts = timeParts[0].split(':'),
    timeSecParts = timeSubParts[2].split('.'),
    timeHours = Number(timeSubParts[0]),
    _date = new Date;

    _date.setUTCFullYear(Number(dateParts[0]));
    _date.setUTCMonth(Number(dateParts[1])-1);
    _date.setUTCDate(Number(dateParts[2]));
    _date.setUTCHours(Number(timeHours));
    _date.setUTCMinutes(Number(timeSubParts[1]));
    _date.setUTCSeconds(Number(timeSecParts[0]));
    if (timeSecParts[1]) _date.setUTCMilliseconds(Number(timeSecParts[1]));

    // by using setUTC methods the date has already been converted to local
    // time(?)
    return _date;
};

namespace.approximatedate = function(current_date) {
    // Display approximate time an event happened when it happened less than 1
    // day ago.
    var now = (new Date).valueOf();
    if (typeof current_date == "string") {
        var timedelta = now - namespace.parse_date(current_date);
    } else {
        var timedelta = now - current_date
    }
    var days = timedelta / 86400000
    var hours = timedelta / 3600000
    var minutes = timedelta / 60000
    var amount = 0
    var unit = ""
    if (days > 1) {
        return 'on ' + Y.Date.format(
            new Date(current_date), {format: '%Y-%m-%d'});
    } else {
        if (hours >= 1) {
            amount = hours
            unit = "hour"
        } else if (minutes >= 1) {
            amount = minutes
            unit = "minute"
        } else {
            return "a moment ago"
        }
        if (Math.floor(amount) > 1) {
            unit = unit + 's'
        }
        return Math.floor(amount) + ' ' + unit + ' ago'
    }
};
}, "0.1", {'requires': ['datatype-date']});
