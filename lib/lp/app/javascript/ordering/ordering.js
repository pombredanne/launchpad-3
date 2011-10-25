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
                ['status', 'Status'],
                ['importance', 'Importance'],
                ['bug-heat-icons', 'Bug heat'],
                ['package', 'Package name'],
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
            var len = keys.length;
            for (var i=0; i<len; i++) {
                var id = keys[i][0];
                var label = keys[i][1];
                var li_html = Y.Lang.substitute(
                    this.constructor.LI_TEMPLATE,
                    {li_id: 'sort-' + id, li_label: label});
                var li_node = Y.Node.create(li_html);
                if (this.get('active') == id) {
                    li_node.addClass('active-sort');
                    // XXX: This needs to be smarter.
                    li_node.one('span').set('innerHTML', '&uarr;');
                }
                orderby_ul.appendChild(li_node);
            }
            this.get('srcNode').appendChild(orderby_ul);
        }
    });

    var ordering = Y.namespace('lp.ordering');
    ordering.OrderBy = OrderBy;

}, '0.1', {'requires': ['widget']});
