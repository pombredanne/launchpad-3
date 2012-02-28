/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Observer table widget.
 *
 * @module lp.registry.disclosure.observertable
 */

YUI.add('lp.registry.disclosure.observertable', function(Y) {

var namespace = Y.namespace('lp.registry.disclosure.observertable');

var
    NAME = "observerTableWidget",
    // Events
    REMOVE_OBSERVER = 'removeObserver';


/*
 * Observer table widget.
 * This widget displays the observers and their level of access to a product.
 */
function ObserverTableWidget(config) {
    ObserverTableWidget.superclass.constructor.apply(this, arguments);
}

ObserverTableWidget.ATTRS = {
    // The duration for various animations eg row deletion.
    animation_duration: {
        value: 1
    },
    // The list of observers to display.
    observers: {
        value: []
    },
    // The access policy types: public, publicsecurity, userdata etc.
    access_policy_types: {
        value: {}
    },
    // The sharing permission choices: all, some, nothing etc.
    sharing_permissions: {
        value: {}
    },
    // The node holding the observer table.
    observer_table: {
        getter: function() {
            return Y.one('#observer-table');
        }
    },
    // The handlebars template for the observer table.
    observer_table_template: {
        value: null
    },
    // The handlebars template for the each access policy item.
    observer_policy_template: {
        value: null
    }
};

Y.extend(ObserverTableWidget, Y.Widget, {

    initializer: function(config) {
        this.set(
            'observer_table_template', this._observer_table_template());
        this.set(
            'observer_policy_template', this._observer_policy_template());
        this.publish(REMOVE_OBSERVER);
    },

    destructor: function() { },

    _observer_table_template: function() {
        return [
            '<table class="disclosure listing" id="observer-table">',
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
            '    <tbody id="observer-table-body">',
            '        {{#observers}}',
            '        <tr id="permission-{{name}}"><td>',
            '            <a href="{{web_link}}" class="sprite person">' +
            '                                  {{display_name}}',
            '            <span class="formHelp">{{role}}</span></a>',
            '        </td>',
            '        <td id="remove-{{name}}">',
            '            <a title="Share nothing with this user"',
            '               href="#" class="sprite remove">',
            '            </a>',
            '        </td>',
            '        <td id="td-permission-{{name}}">',
            '            <span class="sortkey">1</span>',
            '            <ul class="horizontal">',
            '               {{>observer_access_policies}}',
            '            </ul>',
            '        </td>',
            '        <td></td>',
            '        <td><span class="formHelp">No items shared</span>',
            '        </td>',
            '        </tr>',
            '        {{/observers}}',
            '    </tbody>',
            '</table>'].join(' ');
    },

    _observer_policy_template: function() {
        return [
           '{{#access_policies}}',
           '<li><span id="{{policy}}-permission">',
           '  <span class="value"></span>',
           '  <a href="#">',
           '    <img class="editicon sprite edit"/>',
           '  </a>',
           '</span></li>',
           '{{/access_policies}}'].join(' ');
    },

    // Render the popup widget to pick the sharing permission for an
    // access policy.
    renderObserverPolicy: function(
            table_node, observer, policy, current_value) {
        var access_policy_types = this.get('access_policy_types');
        var sharing_permissions = this.get('sharing_permissions');
        var choice_items = [];
        Y.Array.forEach(sharing_permissions, function(permission) {
            var source_name =
                '<strong>{policy_name}:</strong> {permission_name}';
            choice_items.push({
                value: permission.value,
                name: permission.title,
                source_name: Y.Lang.substitute(source_name,
                    {policy_name: access_policy_types[policy],
                     permission_name: permission.title})
            });
        });

        var id = 'permission-'+observer.name;
        var observer_row = table_node.one('#' + id);
        var permission_node = observer_row.one('#td-' + id);
        var contentBox = permission_node.one('#' + policy + '-permission');
        var value_location = contentBox.one('.value');
        var editicon = permission_node.one('img.editicon');

        var permission_edit = new Y.ChoiceSource({
            contentBox: contentBox,
            value_location: value_location,
            editicon: editicon,
            value: current_value,
            title: "Share " + access_policy_types[policy] + " with "
                + observer.display_name,
            items: choice_items,
            elementToFlash: contentBox,
            backgroundColor: '#FFFF99'
        });
        permission_edit.render();
    },

    // Render the access policy values for the observers.
    renderSharingInfo: function(table_node) {
        var observers = this.get('observers');
        var self = this;
        Y.Array.forEach(observers, function(observer) {
            var observer_policies = observer.permissions;
            var policy;
            for (policy in observer_policies) {
                if (observer_policies.hasOwnProperty(policy)) {
                    self.renderObserverPolicy(
                        table_node, observer, policy,
                        observer_policies[policy]);
                }
            }
        });
    },

    renderUI: function() {
        var partials = {
            observer_access_policies:
                this.get('observer_policy_template')
        };
        var observers = this.get('observers');
        Y.Array.forEach(observers, function(observer) {
            var observer_policies = observer.permissions;
            var policy_values = [];
            var policy;
            for (policy in observer_policies) {
                if (observer_policies.hasOwnProperty(policy)) {
                    var policy_value = {policy: policy};
                    policy_values.push(policy_value);
                }
            }
            observer.access_policies = policy_values;
        });

        var html = Y.lp.mustache.to_html(
            this.get('observer_table_template'),
            {observers: observers}, partials);
        var table_node = Y.Node.create(html);
        this.get('observer_table').replace(table_node);
        this.renderSharingInfo(table_node);
    },

    bindUI: function() {
        var observers = this.get('observers');

        var self = this;
        // Bind the delete observer link.
        Y.Array.forEach(observers, function(observer) {
            var link_id = 'remove-' + observer.name;
            var delete_link = self.get('observer_table')
                .one('td#' + link_id + ' a');
            delete_link.on('click', function(e) {
                e.preventDefault();
                self.fire(REMOVE_OBSERVER, delete_link, observer.self_link);
            });
        });
    },

    syncUI: function() { },

    // Delete the specified observer from the table.
    deleteObserver: function(observer) {
        var table_row = this.get('observer_table')
            .one('tr[id=permission-' + observer.name + ']');
        if (!Y.Lang.isValue(table_row)) {
            return;
        }
        var anim_duration = this.get('animation_duration');
        if (anim_duration === 0 ) {
            table_row.remove(true);
            return;
        }
        var anim = Y.lp.anim.red_flash(
            {node: table_row, duration:anim_duration});
        anim.on('end', function() {
            table_row.remove(true);
        });
        anim.run();
    }
});

ObserverTableWidget.NAME = NAME;
ObserverTableWidget.REMOVE_OBSERVER = REMOVE_OBSERVER;
namespace.ObserverTableWidget = ObserverTableWidget;

}, "0.1", { "requires": [
    'node', 'collection', 'lazr.choiceedit',
    'lp.mustache', 'lp.registry.disclosure'] });

