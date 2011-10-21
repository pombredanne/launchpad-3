YUI.add('lp.ordering.test', function(Y) {

var basic_test = Y.namespace('lp.ordering.test');

var suite = new Y.Test.Suite('OrderBy Tests');

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;

suite.add(new Y.Test.Case({

    name: 'order_by_widget_properties',

    test_basic_test: function() {
        var order_widget = new Y.lp.ordering.OrderBy();
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
            expected_sort_keys, order_widget.get('sort_keys'));
    }
}));

basic_test.suite = suite

}, '0.1', {'requires': ['test', 'lp.ordering']});
