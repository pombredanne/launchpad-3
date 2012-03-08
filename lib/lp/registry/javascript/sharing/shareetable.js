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
        value: []
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
    }
};

Y.extend(ShareeTableWidget, Y.Widget, {

    initializer: function(config) {
        this.set(
            'sharee_table_template', this._sharee_table_template());
        this.set(
            'sharee_row_template', this._sharee_row_template());
        this.set(
            'sharee_policy_template', this._sharee_policy_template());
        this.publish(REMOVE_SHAREE);
    },

    destructor: function() { },

    _sharee_table_template: function() {
        return [
            '<table class="sharing listing" id="sharee-table">',
            '    <thead>',
            '        <tr><th style="width: 33%" ' +
            '                      colspan="2">User or Team</th>',
            '            <th colspan="2">',
            '                Sharing',
            '                <span class="help">',
            '                    (<a class="js-action help" target="help"',
            '                        href="permissions_help.html">help</a>)',
            '                </span>',
            '            </th>',
            '            <th style="width: " colspan="1">Shared items</th>',
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
            '<tr id="permission-{{name}}"><td>',
            '    <a href="{{web_link}}" class="sprite person">' +
            '                          {{display_name}}',
            '    <span class="formHelp">{{role}}</span></a>',
            '</td>',
            '<td id="remove-{{name}}">',
            '    <a title="Stop sharing with {{display_name}}"',
            '       href="#" class="sprite remove"' +
            '        data-self_link="{{self_link}}"' +
            '        data-person_name="{{display_name}}">',
            '    </a>',
            '</td>',
            '<td id="td-permission-{{name}}">',
            '    <span class="sortkey">1</span>',
            '    <ul class="horizontal">',
            '       {{>sharee_access_policies}}',
            '    </ul>',
            '</td>',
            '<td></td>',
            '<td><span class="formHelp">No items shared</span>',
            '</td>',
            '</tr>'].join(' ');
    },

    _sharee_policy_template: function() {
        return [
           '{{#information_types}}',
           '<li><span id="{{policy}}-permission-{{sharee_name}}">',
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
        Y.Array.forEach(sharing_permissions, function(permission) {
            var source_name =
                '<strong>{policy_name}:</strong> {permission_name}';
            choice_items.push({
                value: permission.value,
                name: permission.title,
                source_name: Y.Lang.substitute(source_name,
                    {policy_name: information_types[policy],
                     permission_name: permission.title})
            });
        });

        var id = 'permission-'+sharee.name;
        var sharee_row = this.get('sharee_table').one('#' + id);
        var permission_node = sharee_row.one('#td-' + id);
        var contentBox = permission_node.one('#' + policy + '-' + id);
        var value_location = contentBox.one('.value');
        var editicon = permission_node.one('a.editicon');

        var permission_edit = new Y.ChoiceSource({
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
    },

    // Render the access policy values for the sharees.
    render_sharing_info: function() {
        var sharees = this.get('sharees');
        var self = this;
        Y.Array.forEach(sharees, function(sharee) {
            self.render_sharee_sharing_info(sharee);
        });
    },

    // Render the access policy values for an sharee.
    render_sharee_sharing_info: function(sharee) {
        var sharee_policies = sharee.permissions;
        var self = this;
        Y.each(sharee_policies, function(policy_value, policy) {
            self.render_sharee_policy(sharee, policy, policy_value);
        });
    },

    renderUI: function() {
        var partials = {
            sharee_access_policies:
                this.get('sharee_policy_template'),
            sharee_row: this.get('sharee_row_template')
        };
        var sharees = this.get('sharees');
        this._prepareShareeDisplayData(sharees);
        var html = Y.lp.mustache.to_html(
            this.get('sharee_table_template'),
            {sharees: sharees}, partials);
        var table_node = Y.Node.create(html);
        this.get('sharee_table').replace(table_node);
        this.render_sharing_info();
    },

    bindUI: function() {
        // Bind the delete sharee links.
        var self = this;
        this.get('sharee_table').delegate('click', function(e) {
            e.preventDefault();
            var delete_link = e.currentTarget;
            var sharee_link = delete_link.getAttribute('data-self_link');
            var person_name = delete_link.getAttribute('data-person_name');
            self.fire(REMOVE_SHAREE, delete_link, sharee_link, person_name);
        }, 'td[id^=remove-] a');
    },

    syncUI: function() { },

    // Transform the sharee access policy data from the model into a form
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

    // Add a new sharee to the table.
    add_sharee: function(sharee) {
        this._prepareShareeDisplayData([sharee]);
        var partials = {
            sharee_access_policies:
                this.get('sharee_policy_template')
        };
        var row_html = Y.lp.mustache.to_html(
            this.get('sharee_row_template'), sharee, partials);
        var new_table_row = Y.Node.create(row_html);
        var first_row = this.get('sharee_table')
            .one('tbody>:first-child');
        var row_node;
        if (Y.Lang.isValue(first_row)) {
            row_node = first_row.insertBefore(new_table_row, first_row);
        } else {
            row_node = this.get('sharee_table').one('tbody')
                .appendChild(new_table_row);
        }
        this.render_sharee_sharing_info(sharee);
        var anim_duration = this.get('anim_duration');
        var anim = Y.lp.anim.green_flash(
            {node: row_node, duration:anim_duration});
        anim.run();
    },

    // Delete the specified sharee from the table.
    delete_sharee: function(sharee) {
        var table_row = this.get('sharee_table')
            .one('tr[id=permission-' + sharee.name + ']');
        if (!Y.Lang.isValue(table_row)) {
            return;
        }
        var anim_duration = this.get('anim_duration');
        if (anim_duration === 0 ) {
            table_row.remove(true);
            return;
        }
        var anim = Y.lp.anim.green_flash(
            {node: table_row, duration:anim_duration});
        anim.on('end', function() {
            table_row.remove(true);
        });
        anim.run();
    }
});

ShareeTableWidget.NAME = NAME;
ShareeTableWidget.REMOVE_SHAREE = REMOVE_SHAREE;
namespace.ShareeTableWidget = ShareeTableWidget;

}, "0.1", { "requires": [
    'node', 'event', 'collection', 'lazr.choiceedit',
    'lp.mustache', 'lp.registry.sharing.shareepicker'] });

