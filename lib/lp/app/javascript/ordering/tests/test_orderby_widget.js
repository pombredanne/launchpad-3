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
            ['bugnumber', 'Bug number'],
            ['bugtitle', 'Bug title'],
            ['importance', 'Importance'],
            ['status', 'Status'],
            ['package', 'Package name'],
            ['bug-heat-icons', 'Bug heat'],
            ['milestone', 'Milestone'],
            ['assignee', 'Assignee'],
            ['bug-age', 'Bug age']
        ];
        // We have to unpack each item, due to array equality in JavaScript.
        var expected_ids = [];
        var expected_names = [];
        var len = expected_sort_keys.length;
        for (var i=0; i<len; i++) {
            expected_ids.push(expected_sort_keys[i][0]);
            expected_names.push(expected_sort_keys[i][1]);
        }
        var actual_ids = [];
        var actual_names = [];
        var sort_keys = orderby.get('sort_keys');
        var sort_keys_len = sort_keys.length;
        for (var i=0; i<sort_keys_len; i++) {
            actual_ids.push(sort_keys[i][0]);
            actual_names.push(sort_keys[i][1]);
        }
        ArrayAssert.itemsAreSame(expected_ids, actual_ids);
        ArrayAssert.itemsAreSame(expected_names, actual_names);
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
    },

//    test_render_list_items: function() {
//        // Expected
//        var expected_html = '<ul id="bug-order-by-buttons">' +
//            '<li id="sort-id">Bug number</li>' +
//            '<li id="sort-title">Bug title</li>' +
//            '<li id="sort-status">Status</li>' +
//            '<li id="sort-importance" class="active-sort">Importance' +
//            '    <span class="sort-arr desc">&uarr;</span>' +
//            '</li>' +
//            '<li id="sort-heat">Bug heat</li>' +
//            '<li id="sort-package">Package name</li>' +
//            '</ul>'
//        var expected_node = Y.Node.create(expected_html);
//        var expected_li_nodes = expected_node.all('li')._nodes;
//        // Actual
//        var parent_node = Y.Node.create('<div></div>');
//        parent_node.set('id', 'test-div');
//        Y.one('body').appendChild(parent_node);
//        var orderby = new Y.lp.ordering.OrderBy({
//            srcNode: Y.one('#test-div')
//        });
//        orderby.render();
//        var actual_li_nodes = Y.one('#test-div').all('li')._nodes;
//        ArrayAssert.itemsAreEqual(expected_li_nodes, actual_li_nodes)
//    },
//
//    test_render_active_sort_default: function() {
//        var expected_li_node = Y.Node.create(
//            '<li id="sort-importance" class="active-sort">');
//        var parent_node = Y.Node.create('<div></div>');
//        parent_node.set('id', 'test-div');
//        Y.one('body').appendChild(parent_node);
//        var orderby = new Y.lp.ordering.OrderBy({
//            srcNode: Y.one('#test-div')
//        });
//        var actual_li_node = Y.one('#sort-importance');
//        Assert.areEqual(expected_li_node, actual_li_node);
//    },
//
//    test_render_active_sort_user_supplied: function() {
//        var expected_li_node = Y.Node.create(
//            '<li id="sort-importance" class="active-sort">');
//        var parent_node = Y.Node.create('<div></div>');
//        parent_node.set('id', 'test-div');
//        Y.one('body').appendChild(parent_node);
//        var orderby = new Y.lp.ordering.OrderBy({
//            srcNode: Y.one('#test-div'),
//            active_node: 'status'
//        });
//        var actual_li_node = Y.one('#sort-importance');
//        Assert.areEqual(expected_li_node, actual_li_node);
//    }

}));

basic_test.suite = suite

}, '0.1', {'requires': ['test', 'lp.ordering']});
