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

        sort_clause: {
            value: null
        },

        li_nodes: {
            value: null
        }
    }

    OrderBy.LI_TEMPLATE = [
        '<li id="{li_id}">{li_label}',
        '<span class="sort-arr"></span></li>'].join('');

    Y.extend(OrderBy, Y.Widget, {

        _fireSortEvent: function() {
            var prefix = '';
            if (this.get('sort_order') == 'desc') {
                prefix = '-';
            }
            var sort_clause = prefix + this.get('active');
            this.set('sort_clause', sort_clause);
            var event_name = this.constructor.NAME + ':sort';
            Y.fire(event_name, sort_clause);
        },

        _updateSortArrows: function(
            clicked_node, clicked_node_sort_key, preclick_sort_key) {
            // References to the span holding the arrow and the arrow HTML.
            var arrow_span = clicked_node.one('span');
            var up_arrow = Y.Node.create('&uarr;').get('text');
            var down_arrow = Y.Node.create('&darr;').get('text');

            var is_active_sort_button = false;
            if (clicked_node_sort_key == preclick_sort_key) {
                is_active_sort_button = true;
            }
            if (is_active_sort_button) {
                // Handle the case where the button clicked is the current
                // active sort order.  We change sort directions for it.
                var current_arrow = arrow_span.get('innerHTML');
                if (current_arrow == up_arrow) {
                    arrow_span.set('innerHTML', down_arrow);
                    arrow_span.addClass('asc');
                    arrow_span.removeClass('desc');
                    this.set('sort_order', 'asc');
                } else {
                    arrow_span.set('innerHTML', up_arrow);
                    arrow_span.addClass('desc');
                    arrow_span.removeClass('asc');
                    this.set('sort_order', 'desc');
                }
            } else {
                // We have a different sort order clicked and need to
                // remove arrow from recently active sort button as
                // well as add an arrow to a new button.
                var old_active_sort_key = '#sort-' + preclick_sort_key;
                var old_active_li = this.get('contentBox').one(
                    old_active_sort_key);
                var old_arrow_span = old_active_li.one('span');
                old_arrow_span.set('innerHTML', '');
                var pre_click_sort_order = this.get('sort_order');
                old_arrow_span.removeClass(pre_click_sort_order);
                // Update current li span arrow and set new sort order.
                arrow_span.addClass('asc');
                this.set('sort_order', 'asc');
                arrow_span.set('innerHTML', down_arrow);
            }
        },

        _handleClick: function(clicked_node) {
            // Reverse from the node's ID to the sort key, i.e.
            // "sort-foo" gives us "foo" as the sort key.
            var clicked_node_sort_key = clicked_node.get('id').replace(
                'sort-', '');
            // Get a reference to what was active before click and update
            // the "active" widget state.
            var preclick_sort_key = this.get('active');
            this.set('active', clicked_node_sort_key);
            // Update display and fire events.
            this._updateSortArrows(
                clicked_node, clicked_node_sort_key, preclick_sort_key);
            this._fireSortEvent();
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
                    li_node.one('span').addClass(this.get('sort_order'));
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
