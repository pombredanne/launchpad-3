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
    anim_duration: {
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
    // The handlebars template for the observer table rows.
    observer_row_template: {
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
            'observer_row_template', this._observer_row_template());
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
            '        {{>observer_row}}',
            '        {{/observers}}',
            '    </tbody>',
            '</table>'].join(' ');
    },

    _observer_row_template: function() {
        return [
            '<tr id="permission-{{name}}"><td>',
            '    <a href="{{web_link}}" class="sprite person">' +
            '                          {{display_name}}',
            '    <span class="formHelp">{{role}}</span></a>',
            '</td>',
            '<td id="remove-{{name}}">',
            '    <a title="Share nothing with this user"',
            '       href="#" class="sprite remove"' +
            '        data-self_link="{{self_link}}">',
            '    </a>',
            '</td>',
            '<td id="td-permission-{{name}}">',
            '    <span class="sortkey">1</span>',
            '    <ul class="horizontal">',
            '       {{>observer_access_policies}}',
            '    </ul>',
            '</td>',
            '<td></td>',
            '<td><span class="formHelp">No items shared</span>',
            '</td>',
            '</tr>'].join(' ');
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
    render_observer_policy: function(
            observer, policy, current_value) {
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
        var observer_row = this.get('observer_table').one('#' + id);
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
    render_sharing_info: function() {
        var observers = this.get('observers');
        var self = this;
        Y.Array.forEach(observers, function(observer) {
            self.render_observer_sharing_info(observer);
        });
    },

    // Render the access policy values for an observer.
    render_observer_sharing_info: function(observer) {
        var observer_policies = observer.permissions;
        var policy;
        for (policy in observer_policies) {
            if (observer_policies.hasOwnProperty(policy)) {
                this.render_observer_policy(
                    observer, policy, observer_policies[policy]);
            }
        }
    },

    renderUI: function() {
        var partials = {
            observer_access_policies:
                this.get('observer_policy_template'),
            observer_row: this.get('observer_row_template')
        };
        var observers = this.get('observers');
        this._prepareObserverDisplayData(observers);
        var html = Y.lp.mustache.to_html(
            this.get('observer_table_template'),
            {observers: observers}, partials);
        var table_node = Y.Node.create(html);
        this.get('observer_table').replace(table_node);
        this.render_sharing_info();
    },

    bindUI: function() {
        // Bind the delete observer links.
        var self = this;
        this.get('observer_table').delegate('click', function(e) {
            e.preventDefault();
            var delete_link = e.currentTarget;
            var observer_link = delete_link.getAttribute('data-self_link');
            self.fire(REMOVE_OBSERVER, delete_link, observer_link);
        }, 'td[id^=remove-] a');
    },

    syncUI: function() { },

    // Transform the observer access policy data from the model into a form
    // that can be used with the handlebars template.
    _prepareObserverDisplayData: function(observers) {
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
    },

    // Add a new observer to the table.
    add_observer: function(observer) {
        this._prepareObserverDisplayData([observer]);
        var partials = {
            observer_access_policies:
                this.get('observer_policy_template')
        };
        var row_html = Y.lp.mustache.to_html(
            this.get('observer_row_template'), observer, partials);
        var new_table_row = Y.Node.create(row_html);
        var first_row = this.get('observer_table')
            .one('tbody>:first-child');
        var row_node;
        if (Y.Lang.isValue(first_row)) {
            row_node = first_row.insertBefore(new_table_row, first_row);
        } else {
            row_node = this.get('observer_table').one('tbody')
                .appendChild(new_table_row);
        }
        this.render_observer_sharing_info(observer);
        var anim_duration = this.get('anim_duration');
        var anim = Y.lp.anim.green_flash(
            {node: row_node, duration:anim_duration});
        anim.run();
    },

    // Delete the specified observer from the table.
    delete_observer: function(observer) {
        var table_row = this.get('observer_table')
            .one('tr[id=permission-' + observer.name + ']');
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

ObserverTableWidget.NAME = NAME;
ObserverTableWidget.REMOVE_OBSERVER = REMOVE_OBSERVER;
namespace.ObserverTableWidget = ObserverTableWidget;

}, "0.1", { "requires": [
    'node', 'event', 'collection', 'lazr.choiceedit',
    'lp.mustache', 'lp.registry.disclosure.observerpicker'] });

