/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Sharee table widget.
 *
 * @module lp.registry.sharing.shareetable
 */

YUI.add('lp.registry.sharing.shareetable', function(Y) {

var namespace = Y.namespace('lp.registry.sharing.shareetable');

var
    NAME = "shareeTableWidget",
    // Events
    UPDATE_SHAREE = 'updateSharee',
    UPDATE_PERMISSION = 'updatePermission',
    REMOVE_SHAREE = 'removeSharee';


/*
 * Sharee table widget.
 * This widget displays the sharees and their level of access to a product.
 */
function ShareeTableWidget(config) {
    ShareeTableWidget.superclass.constructor.apply(this, arguments);
}

ShareeTableWidget.ATTRS = {
    // The duration for various animations eg row deletion.
    anim_duration: {
        value: 1
    },
    // The list of sharees to display.
    sharees: {
        value: [],
        // We clone the data passed in so external modifications do not
        // interfere.
        setter: function(value) {
            if (!Y.Lang.isArray(value)) {
                return value;
            }
            return Y.JSON.parse(Y.JSON.stringify(value));
        }
    },
    // The information types: public, embargoedsecurity, userdata etc.
    information_types: {
        value: {}
    },
    // The sharing permission choices: all, some, nothing etc.
    sharing_permissions: {
        value: {}
    },
    // The node holding the sharee table.
    sharee_table: {
        getter: function() {
            return Y.one('#sharee-table');
        }
    },
    // The handlebars template for the sharee table.
    sharee_table_template: {
        value: null
    },
    // The handlebars template for the sharee table rows.
    sharee_row_template: {
        value: null
    },
    // The handlebars template for the each access policy item.
    sharee_policy_template: {
        value: null
    },

    write_enabled: {
        value: false
    }
};

Y.extend(ShareeTableWidget, Y.Widget, {

    initializer: function(config) {
        this.set(
            'sharee_table_template', this._sharee_table_template());
        this.set(
            'sharee_row_template', this._sharee_row_template());
        this.set(
            'sharee_table_empty_row', this._sharee_table_empty_row());
        this.set(
            'sharee_policy_template', this._sharee_policy_template());
        this.navigator = this.make_navigator();
        var self = this;
        var ns = Y.lp.registry.sharing.shareelisting_navigator;
        this.navigator.subscribe(
            ns.ShareeListingNavigator.UPDATE_CONTENT, function(e) {
                self._replace_content(e.details[0]);
        });
        this.publish(UPDATE_SHAREE);
        this.publish(UPDATE_PERMISSION);
        this.publish(REMOVE_SHAREE);
    },

    make_navigator: function() {
        var navigation_indices = Y.all('.batch-navigation-index');
        Y.lp.app.listing_navigator.linkify_navigation();
        var ns = Y.lp.registry.sharing.shareelisting_navigator;
        var cache = LP.cache;
        cache.total = this.get('sharees').length;
        var navigator = new ns.ShareeListingNavigator({
            current_url: window.location,
            cache: cache,
            target: Y.one('#sharee-table'),
            navigation_indices: navigation_indices,
            batch_info_template: '<div></div>'
        });
        navigator.set('backwards_navigation', Y.all('.first,.previous'));
        navigator.set('forwards_navigation', Y.all('.last,.next'));
        navigator.clickAction('.first', navigator.first_batch);
        navigator.clickAction('.next', navigator.next_batch);
        navigator.clickAction('.previous', navigator.prev_batch);
        navigator.clickAction('.last', navigator.last_batch);
        navigator.update_navigation_links();
        return navigator;
    },

    _sharee_table_template: function() {
        return [
            '<table class="sharing listing" id="sharee-table">',
            '    <thead>',
            '        <tr><th style="width: 33%" ',
            '                      colspan="2">User or Team</th>',
            '            <th colspan="2">',
            '                Sharing',
            '                <span class="help">',
            '                    (<a class="js-action help" target="help"',
            '                        href="/+help-registry/sharing.html">',
            '                         help',
            '                     </a>)',
            '                </span>',
            '            </th>',
            '            <th colspan="1">Shared items</th>',
            '        </tr>',
            '    </thead>',
            '    <tbody id="sharee-table-body">',
            '        {{#sharees}}',
            '        {{>sharee_row}}',
            '        {{/sharees}}',
            '    </tbody>',
            '</table>'].join(' ');
    },

    _sharee_row_template: function() {
        return [
            '<tr id="permission-{{name}}" data-name="{{name}}"><td>',
            '    <a href="{{web_link}}" class="sprite {{meta}}">',
            '                          {{display_name}}',
            '    <span class="formHelp">{{role}}</span></a>',
            '</td>',
            '<td class="action-icons nowrap">',
            '<span id="remove-{{name}}">',
            '    <a title="Stop sharing with {{display_name}}"',
            '       href="#" class="sprite remove"',
            '        data-self_link="{{self_link}}"',
            '        data-person_name="{{display_name}}">&nbsp;</a>',
            '</span>',
            '<span id="update-{{name}}">',
            '    <a title="Update sharing for {{display_name}}"',
            '       href="#" class="sprite add"',
            '        data-self_link="{{self_link}}"',
            '        data-person_name="{{display_name}}">&nbsp;</a>',
            '</span>',
            '</td>',
            '<td id="td-permission-{{name}}">',
            '    <span class="sortkey">1</span>',
            '    <ul class="horizontal">',
            '       {{>sharee_access_policies}}',
            '    </ul>',
            '</td>',
            '<td></td>',
            '<td>',
            '{{#shared_items_exist}}',
            '<a href="+sharing/{{name}}">View shared items.</a>',
            '{{/shared_items_exist}}',
            '{{^shared_items_exist}}',
            '<span class="formHelp">No items shared.</span>',
            '{{/shared_items_exist}}',
            '</td>',
            '</tr>'].join(' ');
    },

    _sharee_table_empty_row: function() {
        return [
            '<tr id="sharee-table-not-shared">',
            '<td colspan="5" style="padding-left: 0.25em">',
            'This project\'s private information is not shared with ',
            'anyone.',
            '</td></tr>'].join('');
    },

    _sharee_policy_template: function() {
        return [
           '{{#information_types}}',
           '<li class="nowrap">',
           '<span id="{{policy}}-permission-{{sharee_name}}">',
           '  <span class="value"></span>',
           '  <a class="editicon sprite edit" href="#">&nbsp;</a>',
           '</span></li>',
           '{{/information_types}}'].join(' ');
    },

    // Render the popup widget to pick the sharing permission for an
    // access policy.
    render_sharee_policy: function(
            sharee, policy, current_value) {
        var information_types = this.get('information_types');
        var sharing_permissions = this.get('sharing_permissions');
        var choice_items = [];
        Y.each(sharing_permissions, function(title, value) {
            var source_name =
                '<strong>{policy_name}:</strong> {permission_name}';
            choice_items.push({
                value: value,
                name: title,
                source_name: Y.Lang.substitute(source_name,
                    {policy_name: information_types[policy],
                     permission_name: title})
            });
        });

        var id = 'permission-'+sharee.name;
        var sharee_row = this.get('sharee_table').one('[id=' + id + ']');
        var permission_node = sharee_row.one('[id=td-' + id + ']');
        var contentBox = permission_node.one(
            '[id=' + policy + '-' + id + ']');
        var value_location = contentBox.one('.value');
        var editicon = permission_node.one('a.editicon');

        var clickable_content = this.get('write_enabled');
        var permission_edit = new Y.ChoiceSource({
            clickable_content: clickable_content,
            contentBox: contentBox,
            value_location: value_location,
            editicon: editicon,
            value: current_value,
            title: "Share " + information_types[policy] + " with "
                + sharee.display_name,
            items: choice_items,
            elementToFlash: contentBox,
            backgroundColor: '#FFFF99'
        });
        permission_edit.render();
        var self = this;
        permission_edit.on('save', function(e) {
            var permission = permission_edit.get('value');
            self.fire(
                UPDATE_PERMISSION, sharee.self_link, policy, permission);
        });
    },

    // Render the access policy values for the sharees.
    render_sharing_info: function(sharees) {
        var self = this;
        Y.Array.forEach(sharees, function(sharee) {
            self.render_sharee_sharing_info(sharee);
        });
    },

    // Render the access policy values for a sharee.
    render_sharee_sharing_info: function(sharee) {
        var sharee_policies = sharee.permissions;
        var self = this;
        Y.each(sharee_policies, function(policy_value, policy) {
            self.render_sharee_policy(sharee, policy, policy_value);
        });
    },

    _replace_content: function(sharees) {
        LP.cache.sharee_data = sharees;
        this._render_sharees(sharees);
        this.bindUI();
    },

    renderUI: function() {
        this._render_sharees(this.get('sharees'));
    },

    _render_sharees: function(sharees) {
        var sharee_table = this.get('sharee_table');
        var partials = {
            sharee_access_policies:
                this.get('sharee_policy_template'),
            sharee_row: this.get('sharee_row_template')
        };
        this._prepareShareeDisplayData(sharees);
        var html = Y.lp.mustache.to_html(
            this.get('sharee_table_template'),
            {sharees: sharees}, partials);
        var table_node = Y.Node.create(html);
        if (sharees.length === 0) {
            table_node.one('tbody').appendChild(
                Y.Node.create(this.get('sharee_table_empty_row')));
        }
        sharee_table.replace(table_node);
        this.render_sharing_info(sharees);
        this._update_editable_status();
        this.set('sharees', sharees);
    },

    bindUI: function() {
        var sharee_table = this.get('sharee_table');
        // Bind the update and delete sharee links.
        if (!this.get('write_enabled')) {
            return;
        }
        var self = this;
        sharee_table.delegate('click', function(e) {
            e.halt();
            var delete_link = e.currentTarget;
            var sharee_link = delete_link.getAttribute('data-self_link');
            var person_name = delete_link.getAttribute('data-person_name');
            self.fire(REMOVE_SHAREE, delete_link, sharee_link, person_name);
        }, 'span[id^=remove-] a');
        sharee_table.delegate('click', function(e) {
            e.halt();
            var update_link = e.currentTarget;
            var sharee_link = update_link.getAttribute('data-self_link');
            var person_name = update_link.getAttribute('data-person_name');
            self.fire(UPDATE_SHAREE, update_link, sharee_link, person_name);
        }, 'span[id^=update-] a');
    },

    syncUI: function() {
        // Examine the widget's data model and add any new sharees and delete
        // any which have been removed.
        var existing_sharees = this.get('sharees');
        var new_sharees = LP.cache.sharee_data;
        this._prepareShareeDisplayData(new_sharees);
        var new_or_updated_sharees = [];
        var deleted_sharees = [];
        var self = this;
        Y.Array.each(new_sharees, function(sharee) {
            var existing_sharee =
                self._get_sharee_from_model(sharee.name, existing_sharees);
            if (!Y.Lang.isValue(existing_sharee)) {
                new_or_updated_sharees.push(sharee);
            } else {
                if (!self._permissions_equal(
                        sharee.permissions, existing_sharee.permissions)) {
                    new_or_updated_sharees.push(sharee);
                }
            }
        });
        Y.Array.each(existing_sharees, function(sharee) {
            var new_sharee =
                self._get_sharee_from_model(sharee.name, new_sharees);
            if (!Y.Lang.isValue(new_sharee)) {
                deleted_sharees.push(sharee);
            }
        });
        if (new_or_updated_sharees.length > 0) {
            this.update_sharees(new_or_updated_sharees);
        }
        if (deleted_sharees.length > 0) {
            this.delete_sharees(deleted_sharees, new_sharees.length === 0);
        }
        var current_total = existing_sharees.length;
        var total_delta = new_sharees.length - current_total;
        this.navigator.update_batch_totals(new_sharees, total_delta);
        this.set('sharees', new_sharees);
    },

    /**
     * Return true if the permission values in left do not match those in right.
     * @param left
     * @param right
     * @return {Boolean}
     * @private
     */
    _permissions_equal: function(left, right) {
        var result = true;
        Y.some(left, function(sharing_value, info_type) {
            var right_value = right[info_type];
            if (sharing_value !== right_value) {
                result = false;
                return true;
            }
            return false;
        });
        if (!result) {
            return false;
        }
        Y.some(right, function(sharing_value, info_type) {
            var _value = left[info_type];
            if (!Y.Lang.isValue(left[info_type])) {
                result = false;
                return true;
            }
            return false;
        });
        return result;
    },

    /**
     * The the named sharee exists in the model, return it.
     * @param sharee_name
     * @param model
     * @return {*}
     * @private
     */
    _get_sharee_from_model: function(sharee_name, model) {
        var sharee_data = null;
        Y.Array.some(model, function(sharee) {
            if (sharee.name === sharee_name) {
                sharee_data = sharee;
                return true;
            }
            return false;
        });
        return sharee_data;
    },

    // Transform the sharee information type data from the model into a form
    // that can be used with the handlebars template.
    _prepareShareeDisplayData: function(sharees) {
        Y.Array.forEach(sharees, function(sharee) {
            var sharee_policies = sharee.permissions;
            var info_types = [];
            Y.each(sharee_policies, function(policy_value, policy) {
                info_types.push({policy: policy,
                                    sharee_name: sharee.name});
            });
            sharee.information_types = info_types;
        });
    },

    _update_editable_status: function() {
        var sharee_table = this.get('sharee_table');
        if (!this.get('write_enabled')) {
            sharee_table.all(
                '.sprite.add, .sprite.edit, .sprite.remove')
                .each(function(node) {
                    node.addClass('unseen');
            });
        }
    },

    // Add or update new sharees in the table.
    update_sharees: function(sharees) {
        this._prepareShareeDisplayData(sharees);
        var update_node_selectors = [];
        var partials = {
            sharee_access_policies:
                this.get('sharee_policy_template')
        };
        var sharee_table = this.get('sharee_table');
        var self = this;
        Y.Array.each(sharees, function(sharee) {
            var row_html = Y.lp.mustache.to_html(
                self.get('sharee_row_template'), sharee, partials);
            var new_table_row = Y.Node.create(row_html);
            var row_node = sharee_table
                .one('tr[id=permission-' + sharee.name + ']');
            if (Y.Lang.isValue(row_node)) {
                row_node.replace(new_table_row);
            } else {
                // Remove the "No sharees..." row if it's there.
                var not_shared_row = sharee_table.one(
                    'tr#sharee-table-not-shared');
                if (Y.Lang.isValue(not_shared_row)) {
                    not_shared_row.remove(true);
                }
                var first_row = sharee_table.one('tbody>:first-child');
                if (Y.Lang.isValue(first_row)) {
                    first_row.insertBefore(new_table_row, first_row);
                } else {
                    sharee_table.one('tbody').appendChild(new_table_row);
                }
            }
            update_node_selectors.push(
                'tr[id=permission-' + sharee.name + ']');
            self.render_sharee_sharing_info(sharee);
        });
        this._update_editable_status();
        var anim_duration = this.get('anim_duration');
        if (anim_duration === 0) {
            return;
        }
        var anim = Y.lp.anim.green_flash(
            {node: sharee_table.all(
                update_node_selectors.join(',')), duration:anim_duration});
        anim.run();
    },

    // Delete the specified sharees from the table.
    delete_sharees: function(sharees, all_rows_deleted) {
        var deleted_row_selectors = [];
        var sharee_table = this.get('sharee_table');
        Y.Array.each(sharees, function(sharee) {
            var selector = 'tr[id=permission-' + sharee.name + ']';
            var table_row = sharee_table.one(selector);
            if (Y.Lang.isValue(table_row)) {
                deleted_row_selectors.push(selector);
            }
        });
        if (deleted_row_selectors.length === 0) {
            return;
        }
        var rows_to_delete = sharee_table.all(deleted_row_selectors.join(','));
        var delete_rows = function() {
            rows_to_delete.remove(true);
            if (all_rows_deleted === true) {
                sharee_table.one('tbody')
                    .appendChild('<tr id="sharee-table-not-shared"></tr>')
                    .appendChild('<td></td>')
                    .setContent("This project's private information " +
                                "is not shared with anyone.");
            }
        };
        var anim_duration = this.get('anim_duration');
        if (anim_duration === 0 ) {
            delete_rows();
            return;
        }
        var anim = Y.lp.anim.green_flash(
            {node: rows_to_delete, duration:anim_duration});
        anim.on('end', function() {
            delete_rows();
        });
        anim.run();
    }
});

ShareeTableWidget.NAME = NAME;
ShareeTableWidget.UPDATE_SHAREE = UPDATE_SHAREE;
ShareeTableWidget.UPDATE_PERMISSION = UPDATE_PERMISSION;
ShareeTableWidget.REMOVE_SHAREE = REMOVE_SHAREE;
namespace.ShareeTableWidget = ShareeTableWidget;

}, "0.1", { "requires": [
    'node', 'event', 'collection', 'json', 'lazr.choiceedit',
    'lp.mustache', 'lp.registry.sharing.shareepicker',
    'lp.registry.sharing.shareelisting_navigator'
] });

