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
        },

        sort_order: {
            value: 'asc'
        },

        li_nodes: {
            value: null
        }
    }

    OrderBy.LI_TEMPLATE = [
        '<li id="{li_id}">{li_label}',
        '<span class="sort-arr desc"></span></li>'].join('');

    Y.extend(OrderBy, Y.Widget, {

        _handleClick: function(li_node) {
            // Reverse from the node's ID to the sort key, i.e.
            // "sort-foo" gives us "foo" as the sort key.
            var li_node_key = li_node.get('id').replace('sort-', '');

            // Get a reference to what was active before click and update
            // the "active" widget state.
            var pre_click_active = this.get('active');
            this.set('active', li_node_key);

            // If this is the active sort button, we should reverse
            // the arrow currently showing and change the "active" widget
            // state.
            var is_active_sort_button;
            if (li_node_key == pre_click_active) {
                is_active_sort_button = true;
            } else {
                is_active_sort_button = false;
            }
            var up_arrow = Y.Node.create('&uarr;').get('text');
            var down_arrow = Y.Node.create('&darr;').get('text');
            if (is_active_sort_button) {
                var arrow_span = li_node.one('span');
                var current_arrow = arrow_span.get('innerHTML');
                if (current_arrow == up_arrow) {
                    arrow_span.set('innerHTML', down_arrow);
                } else {
                    arrow_span.set('innerHTML', up_arrow);
                }
            }
        },

        renderUI: function() {
            var orderby_ul = Y.Node.create('<ul></ul>');
            var keys = this.get('sort_keys');
            var len = keys.length;
            var li_nodes = [];
            for (var i=0; i<len; i++) {
                var id = keys[i][0];
                var label = keys[i][1];
                var li_html = Y.Lang.substitute(
                    this.constructor.LI_TEMPLATE,
                    {li_id: 'sort-' + id, li_label: label});
                var li_node = Y.Node.create(li_html);
                if (this.get('active') == id) {
                    li_node.addClass('active-sort');
                    var sort_order = this.get('sort_order');
                    if (sort_order == 'asc') {
                        li_node.one('span').set('innerHTML', '&darr;');
                    } else if (sort_order == 'desc') {
                        li_node.one('span').set('innerHTML', '&uarr;');
                    }
                }
                orderby_ul.appendChild(li_node);
                li_nodes.push(li_node);
            }
            this.set('li_nodes', li_nodes);
            this.get('srcNode').appendChild(orderby_ul);
        },

        bindUI: function() {
            var li_nodes = this.get('li_nodes');
            var len = li_nodes.length;
            var that = this;
            for (var i=0; i<len; i++) {
                var li_node = li_nodes[i];
                li_node.on('click', function(e) {
                    that._handleClick(this);
                });
            }
        }
    });

    var ordering = Y.namespace('lp.ordering');
    ordering.OrderBy = OrderBy;

}, '0.1', {'requires': ['widget']});
