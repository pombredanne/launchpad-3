YUI.add('date.test', function (Y) {

    var tests = Y.namespace('date.test');
    tests.suite = new Y.Test.Suite("date tests");

    var now = (new Date).valueOf();
    tests.suite.add(new Y.Test.Case({
        name: 'test_approximatedate',

        test_return_moment_ago: function () {
            Y.Assert.areEqual(
                'a moment ago',
                Y.lp.app.date.approximatedate(new Date(now - 150)));
        },

        test_return_minute_ago: function () {
            Y.Assert.areEqual(
                '1 minute ago',
                Y.lp.app.date.approximatedate(new Date(now - 65000)));
        },

        test_return_hours_ago: function () {
            Y.Assert.areEqual(
                '3 hours ago',
                Y.lp.app.date.approximatedate(new Date(now - 12600000)));
        },

        test_return_days_ago: function () {
            Y.Assert.areEqual(
                'on 2012-08-12', Y.lp.app.date.approximatedate(
                    Y.lp.app.date.parse_date(
                        '2012-08-12T10:00:00.00001+00:00')));
        },

        test_return_in_moment: function () {
            Y.Assert.areEqual(
                'in a moment',
                Y.lp.app.date.approximatedate(new Date(now + 150)));
        },

        test_return_in_hours: function () {
            Y.Assert.areEqual(
                'in 3 hours',
                Y.lp.app.date.approximatedate(new Date(now + 12600000)));
        }

    }));

}, '0.1', {
    requires: ['lp.testing.runner', 'test', 'lp', 'lp.app.date']
});
