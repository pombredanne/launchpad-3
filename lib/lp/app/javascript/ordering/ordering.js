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
                ['bugnumber', 'Bug number'],
                ['bugtitle', 'Bug title'],
                ['importance', 'Importance'],
                ['status', 'Status'],
                ['package', 'Package name'],
                ['bug-heat-icons', 'Bug heat'],
                ['milestone', 'Milestone'],
                ['assignee', 'Assignee'],
                ['bug-age', 'Bug age']
            ]
        },

        active: {
            value: 'importance'
        }
    }

    OrderBy.LI_TEMPLATE = [
        '<li id="{li_id}">{li_label}',
        '<span class="sort-arr desc"></span></li>'].join('');

    Y.extend(OrderBy, Y.Widget, {

        renderUI: function() {
            var orderby_ul = Y.Node.create('<ul></ul>');
            var keys = this.get('sort_keys');
            var len = keys.len;
            for (var i=0; i<len; i++) {
                var li_html = Y.Lang.substitute(
                    this.LI_TEMPLATE,
                    {li_id: 'sort-' + keys[i][0], li_name: keys[i][1]});
                orderby_ul.appendChild(Y.Node.create(li_html));
            }
            this.get('srcNode').appendChild(orderby_ul);
        }
    });

    var ordering = Y.namespace('lp.ordering');
    ordering.OrderBy = OrderBy;

}, '0.1', {'requires': ['widget']});
