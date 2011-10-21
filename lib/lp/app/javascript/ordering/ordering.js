/*
 * An OrderBy Widget.
 */

YUI().add('lp.ordering', function(Y) {

    function OrderBy() {
        OrderBy.superclass.constructor.apply(this, arguments);
    }

    OrderBy.NAME = 'orderby'
    OrderBy.ATTRS = {
        sort_keys: {
            value: [
                'bugnumber',
                'bugtitle',
                'importance',
                'status',
                'package',
                'bug-heat-icons',
                'milestone',
                'assignee',
                'bug-age'
            ]
        }
    }

    Y.extend(OrderBy, Y.Widget, {});

    var ordering = Y.namespace('lp.ordering');
    ordering.OrderBy = OrderBy;

}, '0.1', {'requires': ['widget']});
