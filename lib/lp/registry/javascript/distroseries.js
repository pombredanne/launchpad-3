/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * DistroSeries related stuff.
 *
 * @module registry
 * @submodule distroseries
 */

YUI.add('lp.registry.distroseries.initseries', function(Y) {

Y.log('loading lp.registry.distroseries.initseries');

var namespace = Y.namespace('lp.registry.distroseries.initseries');


/**
 * A form row matching that which LaunchpadForm presents, containing a
 * list of checkboxes, and an optional label and description.
 *
 * @class CheckBoxListWidget
 */
var CheckBoxListWidget = function() {
    CheckBoxListWidget.superclass.constructor.apply(this, arguments);
};

Y.mix(CheckBoxListWidget, {

    NAME: 'checkBoxListWidget',

    ATTRS: {

        /**
         * The field name.
         *
         * @property name
         */
        name: {
            setter: function(value, name) {
                this.fieldNode.all("input").set("name", value);
            }
        },

        /**
         * An array of strings from which to choose.
         *
         * @property choices
         */
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

        /**
         * The top label for the field.
         *
         * @property label
         */
        label: {
            getter: function() {
                return this.labelNode.get("text");
            },
            setter: function(value, name) {
                this.labelNode.set("text", value);
            }
        },

        /**
         * A description shown near the field.
         *
         * @label description
         */
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
        this.spinnerNode = Y.Node.create(
            '<img src="/@@/spinner" alt="Loading..." />');
    },

    renderUI: function() {
        this.get("contentBox")
            .append(this.labelNode)
            .append(this.fieldNode)
            .append(this.descriptionNode);
    },

    /**
     * Show the spinner.
     *
     * @method showSpinner
     */
    showSpinner: function() {
        this.fieldNode.empty().append(this.spinnerNode);
    },

    /**
     * Hide the spinner.
     *
     * @method hideSpinner
     */
    hideSpinner: function() {
        this.spinnerNode.remove();
    },

    /**
     * Display an error.
     *
     * @method showError
     */
    showError: function(error) {
        var message = Y.Node.create('<p />').set("text", error);
        this.fieldNode.empty().append(message);
        Y.lazr.anim.red_flash({node: message}).run();
    }

});

namespace.CheckBoxListWidget = CheckBoxListWidget;


/**
 * A special form of CheckBoxListWidget for choosing architecture tags.
 *
 * @class ArchitecturesCheckBoxListWidget
 */
var ArchitecturesCheckBoxListWidget = function() {
    ArchitecturesCheckBoxListWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(ArchitecturesCheckBoxListWidget, {

    NAME: 'architecturesCheckBoxListWidget',

    ATTRS: {

        /**
         * The DistroSeries the choices in this field should
         * reflect. Takes the form of a string, e.g. "ubuntu/hoary".
         *
         * @property distroSeries
         */
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

        /**
         * The DistroArchSerieses the choices in this field should
         * reflect. Takes the form of a Y.lp.client.Collection.
         *
         * @property distroArchSerieses
         */
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
    }

});

namespace.ArchitecturesCheckBoxListWidget = ArchitecturesCheckBoxListWidget;


/**
 * A special form of CheckBoxListWidget for choosing packagesets.
 *
 * @class PackagesetPickerWidget
 */
var PackagesetPickerWidget = function() {
    PackagesetPickerWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(PackagesetPickerWidget, {

    NAME: 'packagesetPickerWidget',

    ATTRS: {}

});

Y.extend(PackagesetPickerWidget, CheckBoxListWidget, {

    initializer: function(config) {
        this.client = new Y.lp.client.Launchpad();
        this.error_handler = new Y.lp.client.ErrorHandler();
        this.error_handler.clearProgressUI = Y.bind(this.hideSpinner, this);
        this.error_handler.showError = Y.bind(this.showError, this);
    }

});

namespace.PackagesetPickerWidget = PackagesetPickerWidget;


/**
 * Setup the widgets on the +initseries page.
 *
 * @function setup
 */
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
