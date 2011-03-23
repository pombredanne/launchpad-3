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
 * field (defined in a subclass), and an optional label and
 * description.
 *
 * @class FormRowWidget
 */
var FormRowWidget = function() {
    FormRowWidget.superclass.constructor.apply(this, arguments);
};

Y.mix(FormRowWidget, {

    NAME: 'formRowWidget',

    ATTRS: {

        /**
         * The field name.
         *
         * @property name
         */
        name: {
            setter: function(value, name) {
                this.fieldNode.all("input, select").set("name", value);
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

Y.extend(FormRowWidget, Y.Widget, {

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

namespace.FormRowWidget = FormRowWidget;


/**
 * A form row matching that which LaunchpadForm presents, containing a
 * list of checkboxes, and an optional label and description.
 *
 * @class ChoiceListWidget
 */
var ChoiceListWidget = function() {
    ChoiceListWidget.superclass.constructor.apply(this, arguments);
};

Y.mix(ChoiceListWidget, {

    NAME: 'choiceListWidget',

    ATTRS: {

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
                var field_type = this.get("type");
                var list = Y.Node.create("<ul />");
                choices.forEach(
                    function(choice) {
                        var item = Y.Node.create(
                            "<li><input /> <label /></li>");
                        item.one("input")
                            .set("type", field_type)
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
         * The current selection.
         *
         * @property choice
         */
        choice: {
            setter: function(value, name) {
                if (!Y.Lang.isArray(value)) {
                    value = [value];
                }
                this.fieldNode.all("li > input").each(
                    function(node) {
                        node.set(
                            "checked",
                            value.indexOf(node.get("value")) >= 0);
                    }
                );
            },
            getter: function() {
                var choice = [];
                this.fieldNode.all("li > input").each(
                    function(node) {
                        if (node.get("checked")) {
                            choice.push(node.get("value"));
                        }
                    }
                );
                if (this.get("type") == "radio") {
                    if (choice.length == 0) {
                        choice = null;
                    }
                    else if (choice.length == 1) {
                        choice = choice[0];
                    }
                    else {
                        choice = undefined;
                    }
                }
                return choice;
            }
        },

        /**
         * The input type to display. Choose from "checkbox" or "radio".
         *
         * @property type
         */
        type: {
            value: "checkbox",
            setter: function(value, name) {
                this.fieldNode.all("li > input").set("type", value);
            }
        }

    }

});

Y.extend(ChoiceListWidget, FormRowWidget);

namespace.ChoiceListWidget = ChoiceListWidget;


/**
 * A special form of ChoiceListWidget for choosing architecture tags.
 *
 * @class ArchitecturesChoiceListWidget
 */
var ArchitecturesChoiceListWidget = function() {
    ArchitecturesChoiceListWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(ArchitecturesChoiceListWidget, {

    NAME: 'architecturesChoiceListWidget',

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
                if (value.entries.length === 0) {
                    this.fieldNode.append(
                        Y.Node.create('<p />').set(
                            "text",
                            "The chosen series has no architectures!"));
                }
                Y.lazr.anim.green_flash({node: this.fieldNode}).run();
            }
        }
    }

});

Y.extend(ArchitecturesChoiceListWidget, ChoiceListWidget, {

    initializer: function(config) {
        this.client = new Y.lp.client.Launchpad();
        this.error_handler = new Y.lp.client.ErrorHandler();
        this.error_handler.clearProgressUI = Y.bind(this.hideSpinner, this);
        this.error_handler.showError = Y.bind(this.showError, this);
    }

});

namespace.ArchitecturesChoiceListWidget = ArchitecturesChoiceListWidget;


/**
 * A special form of FormRowWidget, containing a select control.
 *
 * @class SelectWidget
 */
var SelectWidget = function() {
    SelectWidget.superclass.constructor.apply(this, arguments);
};

Y.mix(SelectWidget, {

    NAME: 'selectWidget',

    ATTRS: {

        /**
         * An array of objects from which to choose. Each object
         * should contain a value for "value", "text" and "data".
         *
         * @property choices
         */
        choices: {
            getter: function() {
                /* I think this is a YUI3 wart; I can't see any way to
                   map() over a NodeList, so I must push the elements
                   one by one into an array first. */
                var options = Y.Array([]);
                this.fieldNode.all("select > option").each(
                    function(option) { options.push(option); });
                return options.map(
                    function(option) {
                        return {
                            value: option.get("value"),
                            text: option.get("text"),
                            data: option.getData("data")
                        };
                    }
                );
            },
            setter: function(value, name) {
                var select = Y.Node.create("<select />");
                select.set("name", this.get("name"))
                      .set("size", this.get("size"));
                if (this.get("multiple")) {
                    select.set("multiple", "multiple");
                }
                var choices = Y.Array(value);
                choices.forEach(
                    function(choice) {
                        var option = Y.Node.create("<option />");
                        option.set("value", choice.value)
                              .set("text", choice.text)
                              .setData("data", choice.data);
                        select.append(option);
                    }
                );
                if (choices.length > 0) {
                    this.fieldNode.empty().append(select);
                }
                else {
                    this.fieldNode.empty();
                }
            }
        },

        /**
         * The current selection.
         *
         * @property choice
         */
        choice: {
            setter: function(value, name) {
                if (!Y.Lang.isArray(value)) {
                    value = [value];
                }
                this.fieldNode.all("select > option").each(
                    function(node) {
                        node.set(
                            "selected",
                            value.indexOf(node.get("value")) >= 0);
                    }
                );
            },
            getter: function() {
                var choice = [];
                this.fieldNode.all("select > option").each(
                    function(node) {
                        if (node.get("selected")) {
                            choice.push(node.get("value"));
                        }
                    }
                );
                return choice;
            }
        },

        /**
         * The number of rows to show in the select widget.
         *
         * @property size
         */
        size: {
            value: 1,
            setter: function(value, name) {
                this.fieldNode.all("select").set("size", value);
            }
        },

        /**
         * Whether multiple rows can be selected.
         *
         * @property multiple
         */
        multiple: {
            value: false,
            setter: function(value, name) {
                value = value ? true : false;
                this.fieldNode.all("select").set("multiple", value);
                return value;
            }
        }

    }

});

Y.extend(SelectWidget, FormRowWidget, {

    /**
     * Choose a size for the select control based on the number of
     * choices, up to an optional maximum size.
     *
     * @method autoSize
     */
    autoSize: function(maxSize) {
        var choiceCount = this.fieldNode.all("select > option").size();
        if (choiceCount == 0) {
            this.set("size", 1);
        }
        else if (maxSize === undefined) {
            this.set("size", choiceCount);
        }
        else if (choiceCount < maxSize) {
            this.set("size", choiceCount);
        }
        else {
            this.set("size", maxSize);
        }
        return this;
    }

});

namespace.SelectWidget = SelectWidget;


/**
 * A special form of SelectWidget for choosing packagesets.
 *
 * @class PackagesetPickerWidget
 */
var PackagesetPickerWidget = function() {
    PackagesetPickerWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(PackagesetPickerWidget, {

    NAME: 'packagesetPickerWidget',

    ATTRS: {

        /**
         * The DistroSeries the choices in this field should
         * reflect. Takes the form of a string, e.g. "ubuntu/hoary".
         *
         * @property distroSeries
         */
        distroSeries: {
            setter: function(value, name) {
                var distro_series_uri = Y.lp.client.get_absolute_uri(value);
                var on = {
                    start: Y.bind(this.showSpinner, this),
                    success: Y.bind(this.set, this, "packageSets"),
                    failure: this.error_handler.getFailureHandler(),
                    end: Y.bind(this.hideSpinner, this)
                };
                var config = {
                    on: on,
                    parameters: {
                        distroseries: distro_series_uri
                    }
                };
                this.client.named_get("package-sets", "getBySeries", config);
            }
        },

        /**
         * The Packagesets the choices in this field should
         * reflect. Takes the form of a Y.lp.client.Collection.
         *
         * @property packageSets
         */
        packageSets: {
            setter: function(value, name) {
                this.set(
                    "choices", value.entries.map(
                        function(packageset) {
                            return {
                                data: packageset,
                                value: packageset.get("name"),
                                text: (
                                    packageset.get("name") + ": " +
                                    packageset.get("description"))
                            };
                        }
                    )
                );
                if (value.entries.length === 0) {
                    this.fieldNode.append(
                        Y.Node.create('<p />').set(
                            "text",
                            "The chosen series has no package sets!"));
                }
                else {
                    this.autoSize(10);
                }
                Y.lazr.anim.green_flash({node: this.fieldNode}).run();
            }
        }

    }

});

Y.extend(PackagesetPickerWidget, SelectWidget, {

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
    var architecture_choice = new ArchitecturesChoiceListWidget()
        .set("name", "field.architectures")
        .set("label", "Architectures")
        .set("description", (
                 "Choose the architectures you want to " +
                 "use from the parent series."))
        .render(form_table_body);
    var packageset_choice = new PackagesetPickerWidget()
        .set("name", "field.packagesets")
        .set("size", 5)
        .set("multiple", true)
        .set("label", "Package sets to copy from parent")
        .set("description", (
                 "The package sets that will be imported " +
                 "into the derived distroseries."))
        .render(form_table_body);
    var package_copy_options = new ChoiceListWidget()
        .set("name", "field.package_copy_options")
        .set("type", "radio")
        .set("label", "Copy options")
        .set("description", (
                 "Choose whether to rebuild all the sources you copy " +
                 "from the parent, or to copy their binaries too."))
        .set("choices", ["Copy Source and Rebuild",
                         "Copy Source and Binaries"])
        .set("choice", "Copy Source and Binaries")
        .render(form_table_body);
    var derive_from_choice =
        form_table_body.one("[name=field.derived_from_series]");

    // Wire up the distroseries select to the architectures widget.
    function update_architecture_choice() {
        architecture_choice
            .set("distroSeries", derive_from_choice.get("value"));
    }
    derive_from_choice.on("change", update_architecture_choice);

    // Update the architectures widget for the selected distroseries.
    update_architecture_choice();

    // Wire up the distroseries select to the packagesets widget.
    function update_packageset_choice() {
        packageset_choice
            .set("distroSeries", derive_from_choice.get("value"));
    }
    derive_from_choice.on("change", update_packageset_choice);

    // Update the packagesets widget for the selected distroseries.
    update_packageset_choice();

    // Show the form.
    form_container.removeClass("unseen");
};


}, "0.1", {"requires": ["node", "dom", "io", "widget", "lp.client",
                        "lazr.anim", "array-extras"]});
