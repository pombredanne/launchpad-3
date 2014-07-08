/* Copyright 2014 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.app.date', function(Y) {
    
var namespace = Y.namespace('lp.app.date');

namespace.parse_date = function(str) {
    re = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|\+00:00)$/
    bits = re.exec(str).slice(1, 8).map(Number)
    bits[1] -= 1
    return new Date(Date.UTC.apply(null, bits))
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
