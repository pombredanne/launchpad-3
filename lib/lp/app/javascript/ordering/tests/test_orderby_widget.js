YUI.add('lp.ordering.test', function(Y) {

var basic_test = Y.namespace('lp.ordering.test');

var suite = new Y.Test.Suite('OrderBy Tests');

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;

suite.add(new Y.Test.Case({

    name: 'order_by_widget_properties',

    test_default_sort_keys: function() {
        var orderby = new Y.lp.ordering.OrderBy();
        var expected_sort_keys = [
            'bugnumber',
            'bugtitle',
            'importance',
            'status',
            'package',
            'bug-heat-icons',
            'milestone',
            'assignee',
            'bug-age'
        ];
        ArrayAssert.itemsAreEqual(
            expected_sort_keys, orderby.get('sort_keys'));
    },

    test_user_supplied_sort_keys: function() {
        var user_supplied_sort_keys = [
            'foo',
            'bar',
            'baz'
        ];
        var orderby = new Y.lp.ordering.OrderBy({
            sort_keys: user_supplied_sort_keys});
        ArrayAssert.itemsAreEqual(
            user_supplied_sort_keys, orderby.get('sort_keys'));
    }
}));

basic_test.suite = suite

}, '0.1', {'requires': ['test', 'lp.ordering']});
