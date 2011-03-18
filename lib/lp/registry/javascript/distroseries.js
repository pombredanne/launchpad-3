/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Distroseries related stuff.
 *
 * @module Y.lp.registry.distroseries
 * @requires node, DOM
 */
YUI.add('lp.registry.distroseries.initseries', function(Y) {

Y.log('loading lp.registry.distroseries.initseries');

var namespace = Y.namespace('lp.registry.distroseries.initseries');


var CheckBoxListWidget = function() {
    CheckBoxListWidget.superclass.constructor.apply(this, arguments);
};

Y.mix(CheckBoxListWidget, {

    NAME: 'checkBoxListWidget',

    ATTRS: {
        name: {
            setter: function(value, name) {
                this.fieldNode.all("input").set("name", value);
            }
        },
        choices: {
            getter: function() {
                return this.fieldNode.all("li > input").get("value");
            },
            setter: function(value, name) {
                var choices = Y.Array.unique(value).sort();
                var field_name = this.get("name");
                var list = Y.Node.create("<ul />");
                choices.forEach(
                    function(choice) {
                        var item = Y.Node.create(
                            "<li><input /> <label /></li>");
                        item.one("input")
                            .set("type", "checkbox")
                            .set("name", field_name)
                            .set("value", choice);
                        item.one("label")
                            .setAttribute(
                                "for", item.one("input").generateID())
                            .setStyle("font-weight", "normal")
                            .set("text", choice);
                        list.append(item);
                    }
                );
                this.fieldNode.empty().append(list);
            }
        },
        label: {
            getter: function() {
                return this.labelNode.get("text");
            },
            setter: function(value, name) {
                this.labelNode.set("text", value);
            }
        },
        description: {
            getter: function() {
                return this.descriptionNode.get("text");
            },
            setter: function(value, name) {
                this.descriptionNode.set("text", value);
            }
        }
    }

});

Y.extend(CheckBoxListWidget, Y.Widget, {

    BOUNDING_TEMPLATE: "<tr></tr>",

    CONTENT_TEMPLATE: '<td colspan="2"></td>',

    initializer: function(config) {
        this.labelNode = Y.Node.create("<label />");
        this.fieldNode = Y.Node.create("<div></div>");
        this.descriptionNode = Y.Node.create('<p class="formHelp" />');
    },

    renderUI: function() {
        this.get("contentBox")
            .append(this.labelNode)
            .append(this.fieldNode)
            .append(this.descriptionNode);
    }

});

namespace.CheckBoxListWidget = CheckBoxListWidget;


var ArchitecturesCheckBoxListWidget = function() {
    ArchitecturesCheckBoxListWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(ArchitecturesCheckBoxListWidget, {

    NAME: 'architecturesCheckBoxListWidget',

    ATTRS: {
        distroSeries: {
            setter: function(value, name) {
                var path = value + "/architectures";
                var on = {
                    start: Y.bind(this.showSpinner, this),
                    success: Y.bind(this.set, this, "distroArchSerieses"),
                    failure: this.error_handler.getFailureHandler(),
                    end: Y.bind(this.hideSpinner, this)
                };
                this.client.get(path, {on: on});
            }
        },
        distroArchSerieses: {
            setter: function(value, name) {
                this.set(
                    "choices", value.entries.map(
                        function(das) {
                            return das.get("architecture_tag");
                        }
                    )
                );
                if (value.entries.length == 0) {
                    this.fieldNode.append(
                        Y.Node.create('<p />').set(
                            "text", "The chosen series has no architectures!"));
                }
                Y.lazr.anim.green_flash({node: this.fieldNode}).run();
            }
        }
    }

});

Y.extend(ArchitecturesCheckBoxListWidget, CheckBoxListWidget, {

    initializer: function(config) {
        this.client = new Y.lp.client.Launchpad();
        this.error_handler = new Y.lp.client.ErrorHandler();
        this.error_handler.clearProgressUI = Y.bind(this.hideSpinner, this);
        this.error_handler.showError = Y.bind(this.showError, this);
        this.spinner = Y.Node.create(
            '<img src="/@@/spinner" alt="Loading..." />');
    },

    showSpinner: function() {
        this.fieldNode.empty().append(this.spinner);
    },

    hideSpinner: function() {
        this.spinner.remove();
    },

    showError: function(error) {
        var message = Y.Node.create('<p />').set("text", error);
        this.fieldNode.empty().append(message);
        Y.lazr.anim.red_flash({node: message}).run();
    }

});

namespace.ArchitecturesCheckBoxListWidget = ArchitecturesCheckBoxListWidget;


namespace.setup = function() {
    var form_container = Y.one("#init-series-form-container");
    var form_table_body = form_container.one("table.form > tbody");
    var architecture_choice = new ArchitecturesCheckBoxListWidget()
        .set("name", "field.architectures")
        .set("label", "Architectures")
        .set("description", (
                 "Choose the architectures you want to " +
                 "use from the parent series."))
        .render(form_table_body);

    // Wire up the distroseries select to the architectures widget.
    var field_derived_from_series =
        form_table_body.one("[name=field.derived_from_series]");
    function update_architecture_choice() {
        architecture_choice
            .set("distroSeries", field_derived_from_series.get("value"));
    }
    field_derived_from_series.on("change", update_architecture_choice);

    // Update the architectures widget for the selected distroseries.
    update_architecture_choice();

    // Show the form.
    form_container.removeClass("unseen");
};


}, "0.1", {"requires": ["node", "dom", "io", "widget", "lp.client",
                        "lazr.anim", "array-extras"]});
