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
    // Events
    REMOVE_OBSERVER = 'removeObserver';


/* Observer table widget */
function ObserverTableWidget(config) {
    ObserverTableWidget.superclass.constructor.apply(this, arguments);
}

ObserverTableWidget.NAME = "observerTableWidget";

ObserverTableWidget.ATTRS = {
    observers: {
        value: []
    },

    access_policy_types: {
        value: {}
    },

    sharing_permissions: {
        value: {}
    },

    observer_table: {
        getter: function() {
            return Y.one('#observer-table')
        }
    }
};

Y.extend(ObserverTableWidget, Y.Widget, {

    initializer: function(config) {
        this.set('observers', config.observers);
        this.publish(REMOVE_OBSERVER);
    },

    destructor : function() { },

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
                name: permission.name,
                source_name: Y.Lang.substitute(source_name,
                    {policy_name: access_policy_types[policy],
                     permission_name: permission.name})
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

    renderUI : function() {
        var observer_table_template =
            Y.one('#observer-table-template').getContent();
        var observer_policy_template =
            Y.one('#observer-access-policy').getContent();
        var partials = {
            observer_access_policies: observer_policy_template
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
            observer_table_template, {observers: observers}, partials);
        var table_node = Y.Node.create(html);
        this.get('observer_table').replace(table_node);
        this.renderSharingInfo(table_node);
    },

    bindUI : function() {
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

    syncUI : function() { },

    deleteObserver: function(observer) {
        var table_row = this.get('observer_table')
            .one('tr[id=permission-' + observer.name + ']');
        if (!Y.Lang.isValue(table_row)) {
            return;
        }
        var anim = Y.lp.anim.red_flash({node: table_row, duration:1});
        anim.on('end', function() {
            table_row.remove(true);
        });
        anim.run();
    }
});

ObserverTableWidget.REMOVE_OBSERVER = REMOVE_OBSERVER;
namespace.ObserverTableWidget = ObserverTableWidget;

}, "0.1", { "requires": [
    'node', 'lp.mustache', 'lp.registry.disclosure'] });

