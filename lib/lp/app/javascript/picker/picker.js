/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI.add('lazr.picker', function(Y) {

/**
 * Module containing the Lazr searchable picker.
 *
 * @module lazr.picker
 * @namespace lazr.picker
 */

/**
 * A picker is a pop-up widget containing a search field and displaying a list
 * of found results.
 *
 * @class Picker
 * @extends lazr.PrettyOverlay
 * @constructor
 */

var PICKER  = 'picker',
    BOUNDING_BOX = 'boundingBox',
    CONTENT_BOX  = 'contentBox',

    // Local aliases
    getCN = Y.ClassNameManager.getClassName,

    // CSS Classes
    C_SEARCH = getCN(PICKER, 'search'),
    C_SEARCH_BOX = getCN(PICKER, 'search-box'),
    C_SEARCH_SLOT = getCN(PICKER, 'search-slot'),
    C_FOOTER_SLOT = getCN(PICKER, 'footer-slot'),
    C_SEARCH_MODE = getCN(PICKER, 'search-mode'),
    C_FILTER = getCN(PICKER, 'filter'),
    C_RESULTS = getCN(PICKER, 'results'),
    C_RESULT_TITLE = getCN(PICKER, 'result-title'),
    C_RESULT_DESCRIPTION = getCN(PICKER, 'result-description'),
    C_ERROR = getCN(PICKER, 'error'),
    C_ERROR_MODE = getCN(PICKER, 'error-mode'),
    C_NO_RESULTS = getCN(PICKER, 'no-results'),
    C_BATCHES = getCN(PICKER, 'batches'),
    C_SELECTED_BATCH = getCN(PICKER, 'selected-batch'),

    // Events
    SAVE = 'save',
    SEARCH = 'search',

    // Property constants
    MIN_SEARCH_CHARS = 'min_search_chars',
    CURRENT_SEARCH_STRING = 'current_search_string',
    ERROR = 'error',
    RESULTS = 'results',
    BATCHES = 'batches',
    BATCH_COUNT = 'batch_count',
    SEARCH_SLOT = 'search_slot',
    FOOTER_SLOT = 'footer_slot',
    SELECTED_BATCH = 'selected_batch',
    SEARCH_MODE = 'search_mode',
    NO_RESULTS_SEARCH_MESSAGE = 'no_results_search_message',
    RENDERUI = "renderUI",
    BINDUI = "bindUI",
    ASSOCIATED_FIELD_ID = 'associated_field_id',
    SELECTED_VALUE = 'selected_value',
    SELECTED_VALUE_METADATA = 'selected_value_metadata',
    FILTER_OPTIONS = 'filter_options',
    CURRENT_FILTER_VALUE = 'current_filter_value';


var Picker = function () {
    Picker.superclass.constructor.apply(this, arguments);

    Y.after(this._renderUIPicker, this, RENDERUI);
    Y.after(this._bindUIPicker, this, BINDUI);
    Y.after(this._syncUIPicker, this, BINDUI);
};

Y.extend(Picker, Y.lazr.PrettyOverlay, {
    /**
     * The search input box node.
     *
     * @property _search_input
     * @type Node
     * @private
     */
    _search_input: null,

    /**
     * The search button node.
     *
     * @property _search_button
     * @type Node
     * @private
     */
    _search_button: null,

    /**
     * The node containing filter options.
     *
     * @property _filter_box
     * @type Node
     * @private
     */
    _filter_box: null,

    /**
     * The node containing search results.
     *
     * @property _results_box
     * @type Node
     * @private
     */
    _results_box: null,

    /**
     * The node containing the extra form inputs.
     *
     * @property _search_slot_box
     * @type Node
     * @private
     */
    _search_slot_box: null,

    /**
     * The node containing the batches.
     *
     * @property _batches_box
     * @type Node
     * @private
     */
    _batches_box: null,

    /**
     * The node containing the previous batch button.
     *
     * @property _prev_button
     * @type Node
     * @private
     */
    _prev_button: null,

    /**
     * The node containing the next batch button.
     *
     * @property _next_button
     * @type Node
     * @private
     */
    _next_button: null,

    /**
     * The node containing an error message if any.
     *
     * @property _error_box
     * @type Node
     * @private
     */
    _error_box: null,

    initializer: function(cfg) {
        /**
         * Fires when the user presses the 'Search' button.
         * The event details contain the search string entered by the user.
         *
         * This event is only fired if the search string is longer than the
         * min_search_chars attribute.
         *
         * This event is also fired when the user clicks on one of the batch
         * items, the details then contain both the previous search string and
         * the value of the batch item selected.
         *
         * @event search
         * @preventable _defaultSearch
         */
        this.publish(SEARCH, { defaultFn: this._defaultSearch });

        /**
         * Fires when the user selects one of the result. The event details
         * contain the value of the selected result.
         *
         * @event save
         * @preventable _defaultSave
         */
        this.publish(SAVE, { defaultFn: this._defaultSave } );

        // Subscribe to the cancel event so that we can clear the widget when
        // requested.
        this.subscribe('cancel', this._defaultCancel);

        if ( this.get('picker_activator') ) {
            var element = Y.one(this.get('picker_activator'));
            element.on('click', function(e) {
                e.halt();
                this.show();
            }, this);
            element.addClass(this.get('picker_activator_css_class'));
        }

        if (!Y.Lang.isUndefined(cfg)) {
            // The picker's associated field.
            if (Y.Lang.isValue(cfg[ASSOCIATED_FIELD_ID])) {
                this.plug(TextFieldPickerPlugin,
                            {input_element:
                                '[id="'+cfg[ASSOCIATED_FIELD_ID]+'"]'});
            }
            // Meta information associated with the picker's associated
            // field's current value.
            if (Y.Lang.isValue(cfg[SELECTED_VALUE_METADATA])) {
                this.set(
                    SELECTED_VALUE_METADATA, cfg[SELECTED_VALUE_METADATA]);
            }
            // The value of the picker's associated field.
            if (Y.Lang.isValue(cfg[SELECTED_VALUE])) {
                this.set(SELECTED_VALUE, cfg[SELECTED_VALUE]);
            }
            // Optional filter support
            if (Y.Lang.isValue(cfg[FILTER_OPTIONS])) {
                this.set(FILTER_OPTIONS, cfg[FILTER_OPTIONS]);
                if (Y.Lang.isValue(cfg[CURRENT_FILTER_VALUE])) {
                    this.set(CURRENT_FILTER_VALUE, cfg[CURRENT_FILTER_VALUE]);
                }
            }
        }
    },

    /**
     * Update the container for extra form inputs.
     *
     * @method _syncSearchSlotUI
     * @protected
     */
    _syncSearchSlotUI: function() {
        var search_slot = this.get(SEARCH_SLOT);

        // Clear previous slot contents.
        this._search_slot_box.set('innerHTML', '');

        if (search_slot !== null) {
            this._search_slot_box.appendChild(search_slot);
        }
    },

    /**
     * Update the container for extra form inputs.
     *
     * @method _syncSearchSlotUI
     * @protected
     */
    _syncFooterSlotUI: function() {
        var footer_slot = this.get(FOOTER_SLOT);

        // Clear previous slot contents.
        this._footer_slot_box.set('innerHTML', '');

        if (footer_slot !== null) {
            this._footer_slot_box.appendChild(footer_slot);
        }
    },

    /**
     * Return the batch page information.
     *
     * @method _getBatches
     * @protected
     */
    _getBatches: function() {
        var batches = this.get(BATCHES);

        if (batches === null) {
            var batch_count = this.get(BATCH_COUNT);
            if (batch_count === null) {
                batches = [];
            }
            else {
                batches = [];
                // Only create batch pages when there's more than one.
                if (batch_count > 1) {
                    var i;
                    for (i = 0; i < batch_count; i++) {
                        batches.push({ value: i, name: i + 1 });
                    }
                }
            }
        }
        return batches;
    },

    /**
     * Update the batches container in the UI.
     *
     * @method _syncBatchesUI
     * @protected
     */
    _syncBatchesUI: function() {
        var batches = this._getBatches();

        // Clear previous batches.
        Y.Event.purgeElement(this._batches_box, true);
        this._batches_box.set('innerHTML', '');

        if (batches.length === 0) {
            this._prev_button = null;
            this._next_button = null;
            return;
        }

        // The enabled property of the prev/next buttons is controlled
        // in _syncSelectedBatchUI.
        this._prev_button = Y.Node.create(Y.lazr.ui.PREVIOUS_BUTTON);
        this._prev_button.on('click', function (e) {
            var selected = this.get(SELECTED_BATCH) - 1;
            this.set(SELECTED_BATCH, selected);
            this.fire(
                SEARCH, this.get(CURRENT_SEARCH_STRING),
                batches[selected].value);
        }, this);
        this._batches_box.appendChild(this._prev_button);

        Y.Array.each(batches, function(data, i) {
            var batch_item = Y.Node.create('<span></span>');
            batch_item.appendChild(
                document.createTextNode(data.name));
            this._batches_box.appendChild(batch_item);

            batch_item.on('click', function (e) {
                this.set(SELECTED_BATCH, i);
                this.fire(
                    SEARCH, this.get(CURRENT_SEARCH_STRING), data.value);
            }, this);
        }, this);

        this._next_button = Y.Node.create(Y.lazr.ui.NEXT_BUTTON);
        this._batches_box.appendChild(this._next_button);
        this._next_button.on('click', function (e) {
            var selected = this.get(SELECTED_BATCH) + 1;
            this.set(SELECTED_BATCH, selected);
            this.fire(
                SEARCH, this.get(CURRENT_SEARCH_STRING),
                batches[selected].value);
        }, this);
    },

    /**
     * Synchronize the selected batch with the UI.
     *
     * @method _syncSelectedBatchUI
     * @protected
     */
    _syncSelectedBatchUI: function() {
        var idx = this.get(SELECTED_BATCH);
        var items = this._batches_box.all('span');
        if (items.size()) {
            this._prev_button.set('disabled', idx === 0);
            items.removeClass(C_SELECTED_BATCH);
            items.item(idx).addClass(C_SELECTED_BATCH);
            this._next_button.set('disabled', idx+1 === items.size());
        }
    },

    /**
     * Return a node containing the specified text. If a href is provided,
     * then the text will be linkified with with the given css class. The
     * link will open in a new window (but the browser can be configured to
     * open a new tab instead if the user so wishes).
     * @param text the text to render
     * @param href the URL of the new window
     * @param css the style to use when rendering the link
     */
    _text_or_link: function(text, href, css) {
        var result;
        if (href) {
            result=Y.Node.create('<a></a>').addClass(css);
            result.set('text', text).set('href', href);
            Y.on('click', function(e) {
                e.halt();
                window.open(href);
            }, result);
        } else {
            result = document.createTextNode(text);
        }
        return result;
    },

    /**
     * Render a node containing the title part of the picker entry.
     * The title will consist of some main text with some optional alternate
     * text which will be rendered in parentheses after the main text. The
     * title/alt_title text may separately be turned into a link with user
     * specified URLs.
     * @param data a json data object with the details to render
     */
    _renderTitleUI: function(data) {
        var li_title = Y.Node.create(
            '<span></span>').addClass(C_RESULT_TITLE);
        if (data.title === undefined) {
            // Display an empty element if data is empty.
            return li_title;
        }
        var title = this._text_or_link(
            data.title, data.title_link, data.link_css);
        li_title.appendChild(title);
        if (data.alt_title) {
            var alt_link = null;
            if (!data.details) {
                // XXX sinzui 2011-08-04: Remove this block when expanders
                // are released.
                if (data.alt_title_link) {
                    alt_link =Y.Node.create('<a></a>')
                        .addClass(data.link_css)
                        .addClass('discreet');
                    alt_link.set('text', " Details...")
                        .set('href', data.alt_title_link);
                    Y.on('click', function(e) {
                        e.halt();
                        window.open(data.alt_title_link);
                    }, alt_link);
                }
            }

            li_title.appendChild('&nbsp;(');
            var alt_title_node = Y.Node.create('<span></span>')
                .set('text', data.alt_title);
            li_title.appendChild(alt_title_node);
            li_title.appendChild(')');
            if (alt_link !== null) {
                // XXX sinzui 2011-08-04: Remove this block when expanders
                // are released.
                li_title.appendChild(Y.Node.create('&nbsp;&nbsp;'));
                li_title.appendChild(alt_link);
            }
        }
        return li_title;
    },

    /**
     * Render a node containing the badge part of the picker entry.
     * A badge is a small image with affiliation details which is displayed
     * next to the title. The display of badges is optional.
     * @param data a json data object with the details to render
     */
    _renderTitleBadgesUI: function(data) {
        var badges = null;
        if (data.badges) {
            badges = Y.Node.create('<div>Affiliation:</div>')
                .addClass('badge');
            var already_processed = [];
            Y.each(data.badges, function(badge_info) {
                var badge_url = badge_info.url;
                var badge_alt = badge_info.label + ' ' + badge_info.role;
                if (already_processed.indexOf(badge_info.label)<0) {
                    already_processed.push(badge_info.label);
                    var badge = Y.Node.create('<img></img>')
                        .addClass('badge')
                        .set('src', badge_url)
                        .set('alt', Y.Escape.html(badge_alt));
                    badges.appendChild(badge);
                }
            });
        } else if (data.target_type) {
            badges = Y.Node.create('<div></div>')
                .set('text', data.target_type)
                .addClass('badge');
        }
        return badges
    },

    /**
     * Render a node containing the description part of the picker entry.
     * @param data a json data object with the details to render
     */
    _renderDescriptionUI: function(data) {
        var li_desc = Y.Node.create(
            '<div><br /></div>').addClass(C_RESULT_DESCRIPTION);
        if (data.description) {
            li_desc.replaceChild(
                document.createTextNode(data.description),
                li_desc.one('br'));
        }
        return li_desc;
    },

    /**
     * Render a node containing the optional details part of the picker entry.
     * @param data a json data object with the details to render
     */
    _renderDetailsUI: function(data) {
        if (!data.details && !data.badges) {
            return null;
        }
        var details_node = Y.Node.create('<div></div>')
            .addClass('sprite')
            .addClass(C_RESULT_DESCRIPTION);
        if (Y.Lang.isArray(data.details)) {
            var data_node = Y.Node.create('<div></div>');
            var escaped_details = [];
            Y.Array.each(data.details, function(detail) {
                escaped_details.push(Y.Escape.html(detail));
                });
            data_node.append(Y.Node.create(escaped_details.join('<br />')));
            details_node.append(data_node);
        }
        if (Y.Lang.isArray(data.badges)) {
            var already_processed = [];
            Y.each(data.badges, function(badge_info) {
                if (already_processed.indexOf(badge_info.label)<0) {
                    already_processed.push(badge_info.label);
                    var affiliation = Y.Node.create('<div></div>')
                        .addClass('affiliation');
                    var badge_text = badge_info.label + ' ' + badge_info.role;
                    var badge = Y.Node.create('<img></img>')
                        .set('src', badge_info.url)
                        .set('alt', Y.Escape.html(badge_text));
                    affiliation.appendChild(badge);
                    affiliation.appendChild(Y.Node.create('Affiliation'));
                    details_node.append(affiliation);
                    var affiliation_text = Y.Node.create('<div></div>')
                        .addClass('affiliation-text');
                    affiliation_text.appendChild(Y.Node.create(badge_text));
                    details_node.append(affiliation_text);
                }
            });
        }
        var links = [];
        links.push(Y.Node.create(
            '<a class="sprite yes save" href="#"></a>')
                .set('text', 'Select ' + data.title));
        links[0].on('click', function (e, value) {
            e.preventDefault();
            this.fire(SAVE, value);
            }, this, data);
        links.push(this._text_or_link(
            'View details', data.alt_title_link, data.link_css));
        var link_list = Y.Node.create('<ul></ul>')
            .addClass('horizontal');
        Y.Array.each(links, function(link, i) {
            var li = Y.Node.create('<li></li>');
            li.append(link);
            link_list.append(li);
            });
        details_node.append(link_list);
        return details_node;
    },

    /**
     * Update the UI based on the results attribute.
     *
     * @method _syncResultsUI
     * @protected
     */
    _syncResultsUI: function() {
        var results = this.get(RESULTS);

        // Remove any previous results.
        Y.Event.purgeElement(this._results_box, true);
        this._results_box.set('innerHTML', '');
        this._filter_box.set('innerHTML', '');

        var expander_id = this.get(BOUNDING_BOX).get('id');
        Y.Array.each(results, function(data, i) {
            // Sort out the badges div.
            var li_badges = this._renderTitleBadgesUI(data);
            // Sort out the title span.
            var li_title = this._renderTitleUI(data);
            // Sort out the description div.
            var li_desc = this._renderDescriptionUI(data);
            // Sort out the optional details div.
            var li_details = this._renderDetailsUI(data);
            // Put the list item together.
            var li = Y.Node.create('<li></li>').addClass(
                i % 2 ? Y.lazr.ui.CSS_ODD : Y.lazr.ui.CSS_EVEN);
            if (data.css) {
                li.addClass(data.css);
            }
            if (data.image) {
                li.appendChild(
                    Y.Node.create('<img />').set('src', data.image));
            }
            if (li_badges !== null) {
                li.appendChild(li_badges);
            }
            li.appendChild(li_title);
            li.appendChild(li_desc);
            if (li_details) {
                // Use explicit save link.
                if (li_desc.get('text') === '') {
                    li_desc.set('text', 'More information...');
                }
                li.appendChild(li_details);
                li.expander = new Y.lp.app.widgets.expander.Expander(
                    li_desc, li_details, {group_id: expander_id});
                li.expander.setUp();
                li_title.on('click', function (e, value) {
                    this.fire(SAVE, value);
                    }, this, data);
            } else {
                // Attach implicit save handler.
                li.on('click', function (e, value) {
                    this.fire(SAVE, value);
                    }, this, data);
            }

            this._results_box.appendChild(li);
        }, this);

        // If the user has entered a search and there ain't no results,
        // display the message about no items matching.
        if (this._search_input.get('value') && !results.length) {
            var msg = Y.Node.create('<li></li>');
            msg.appendChild(
                document.createTextNode(
                    Y.substitute(this.get(NO_RESULTS_SEARCH_MESSAGE),
                    {query: this._search_input.get('value')})));
            this._results_box.appendChild(msg);
            this._results_box.addClass(C_NO_RESULTS);
            this._syncFilterUI();
        } else {
            this._results_box.removeClass(C_NO_RESULTS);
            if (results.length) {
                var filters = this.get(FILTER_OPTIONS);
                var current_filter_value = this.get(CURRENT_FILTER_VALUE);
                if (filters.length  > 0 &&
                        !Y.Lang.isValue(current_filter_value)) {
                    this.set(CURRENT_FILTER_VALUE, filters[0].title);
                }
                this._syncFilterUI();
            }
        }

        if (results.length) {
            // Set PrettyOverlay's green progress bar to 100%.
            this.set('progress', 100);
        } else {
            // Set PrettyOverlay's green progress bar to 50%.
            this.set('progress', 50);
        }
    },

    /**
     * Update the filter UI based on the current filter value used for the
     * search.
     */
    _syncFilterUI: function() {
        // Check that we need to display the filter UI.
        var filters = this.get(FILTER_OPTIONS);
        if( filters.length === 0 ) {
            return;
        }
        var current_filter_value = this.get(CURRENT_FILTER_VALUE);
        if (!Y.Lang.isValue(current_filter_value)) {
            return;
        }

        var filter_msg = Y.substitute(
            'Showing <strong>{filter}</strong> matches for "{search_terms}".',
            {filter: current_filter_value,
            search_terms: this._search_input.get('value')});
        this._filter_box.appendChild(Y.Node.create(filter_msg));

        var filter_node = Y.Node.create('<div>Filter by:&nbsp;</div>');
        var picker = this;
        Y.Array.each(filters, function(filter, i) {
            var filter_link = Y.Node.create('<a></a>')
                .set('href', '#')
                .set('text', filter.title)
                .set('title', filter.description);
            if( filter.title === current_filter_value) {
                filter_link.addClass('invalid-link');
            } else {
                filter_link.addClass('js-action');
                // When a filter link is clicked, we simply fire off a search
                // event.
                filter_link.on('click', function (e) {
                    e.halt();
                    picker.set(CURRENT_FILTER_VALUE, filter.title);
                    var search_string = Y.Lang.trim(
                        picker._search_input.get('value'));
                    picker._performSearch(search_string, filter.name);
                });
            }
            filter_node.append(filter_link);
            if (i < filters.length - 2) {
                filter_node.append(Y.Node.create(',&nbsp;'));
            } else if (i === filters.length - 2) {
                filter_node.append(Y.Node.create(',&nbsp;or&nbsp;'));
            }
        });
        this._filter_box.appendChild(filter_node);
    },

    /**
     * Sync UI with search mode. Disable the search input and button.
     *
     * @method _syncSearchModeUI
     * @protected
     */
    _syncSearchModeUI: function() {
        var search_mode = this.get(SEARCH_MODE);
        this._search_input.set('disabled', search_mode);
        this._search_button.set('disabled', search_mode);
        if (search_mode) {
            this.get(BOUNDING_BOX).addClass(C_SEARCH_MODE);
        } else {
            this.get(BOUNDING_BOX).removeClass(C_SEARCH_MODE);
            // If the search input isn't blurred before it is focused,
            // then the I-beam disappears.
            this._search_input.blur();
            this._search_input.focus();
        }
    },

    /**
     * Sync UI with the error message.
     *
     * @method _syncErrorUI
     * @protected
     */
    _syncErrorUI: function() {
        var error = this.get(ERROR);
        this._error_box.set('innerHTML', '');
        if (error === null) {
            this.get(BOUNDING_BOX).removeClass(C_ERROR_MODE);
        } else {
            this._error_box.appendChild(document.createTextNode(error));
            this.get(BOUNDING_BOX).addClass(C_ERROR_MODE);
        }
    },

    /**
     * Create the widget's HTML components.
     * <p>
     * This method is invoked after renderUI is invoked for the Widget class
     * using YUI's aop infrastructure.
     * </p>
     *
     * @method _renderUIPicker
     * @protected
     */
    _renderUIPicker: function() {
        this._search_button = Y.Node.create(Y.lazr.ui.SEARCH_BUTTON);

        var search_box = Y.Node.create([
            '<div>',
            '<input type="text" size="20" name="search" ',
            'autocomplete="off"/>',
            '<div></div></div>'].join(""));

        this._search_input = search_box.one('input');
        this._search_input.addClass(C_SEARCH);

        this._error_box = search_box.one('div');
        this._error_box.addClass(C_ERROR);

        // The search button is floated right to avoid problems with
        // the input width in Safari 3.
        search_box.insertBefore(this._search_button, this._search_input);
        search_box.addClass(C_SEARCH_BOX);

        this._search_slot_box = Y.Node.create('<div></div>');
        this._search_slot_box.addClass(C_SEARCH_SLOT);
        search_box.appendChild(this._search_slot_box);

        this._filter_box = Y.Node.create('<div></div>');
        this._filter_box.addClass(C_FILTER);

        this._results_box = Y.Node.create('<ul></ul>');
        this._results_box.addClass(C_RESULTS);

        this._batches_box = Y.Node.create('<div></div>');
        this._batches_box.addClass(C_BATCHES);

        this._footer_slot_box = Y.Node.create('<div></div>');
        this._footer_slot_box.addClass(C_FOOTER_SLOT);

        var body = Y.Node.create('<div></div>');
        body.appendChild(search_box);
        body.appendChild(this._filter_box);
        body.appendChild(this._results_box);
        body.appendChild(this._batches_box);
        body.appendChild(this._footer_slot_box);
        body.addClass('yui3-widget-bd');

        this.setStdModContent(
            Y.WidgetStdMod.BODY, body, Y.WidgetStdMod.APPEND);
    },

    /**
     * Bind the widget's DOM elements to their event handlers.
     * <p>
     * This method is invoked after bindUI is invoked for the Widget class
     * using YUI's aop infrastructure.
     * </p>
     *
     * @method _bindUIPicker
     * @protected
     */
    _bindUIPicker: function() {
        Y.on('click', this._defaultSearchUserAction, this._search_button,
             this);

        // Enter key
        Y.on(
            'key', this._defaultSearchUserAction, this._search_input,
            'down:13', this);

        // Focus search box when the widget is first displayed.
        this.after('visibleChange', function (e) {
            var change = e.details[0];
            if (change.newVal === true && change.prevVal === false) {
                // The widget has to be centered before the search
                // input is focused, so that it is centered in the current
                // viewport and not the viewport after scrolling to the
                // widget.
                this.set('centered', true);
                this._search_input.focus();
            }
        }, this);

        // Update the display whenever the "results" property is changed and
        // clear the search mode.
        this.after('resultsChange', function (e) {
            this._syncResultsUI();
            this.set(SEARCH_MODE, false);
        }, this);

        // Update the search slot box whenever the "search_slot" property
        // is changed.
        this.after('search_slotChange', function (e) {
            this._syncSearchSlotUI();
        }, this);

        // Update the footer slot box whenever the "footer_slot" property
        // is changed.
        this.after('footer_slotChange', function (e) {
            this._syncFooterSlotUI();
        }, this);

        // Update the batch list whenever the "batches" or "results" property
        // is changed.
        var doBatchesChange = function (e) {
            this._syncBatchesUI();
            this._syncSelectedBatchUI();
        };

        this.after('batchesChange', doBatchesChange, this);
        this.after('resultsChange', doBatchesChange, this);

        // Keep the UI in sync with the currently selected batch.
        this.after('selected_batchChange', function (e) {
            this._syncSelectedBatchUI();
        }, this);

        // Update the display whenever the "results" property is changed.
        this.after('search_modeChange', function (e) {
            this._syncSearchModeUI();
        }, this);

        // Update the display whenever the "error" property is changed.
        this.after('errorChange', function (e) {
            this._syncErrorUI();
        });
    },

    /**
     * Synchronize the search box, error message and results with the UI.
     * <p>
     * This method is invoked after syncUI is invoked for the Widget class
     * using YUI's aop infrastructure.
     * </p>
     *
     * @method _syncUIPicker
     * @protected
     */
    _syncUIPicker: function() {
        this._syncResultsUI();
        this._syncSearchModeUI();
        this._syncBatchesUI();
        this._syncSelectedBatchUI();
        this._syncErrorUI();
        this._search_input.focus();
    },

    /*
     * Clear all elements of the picker, resetting it to its original state.
     *
     * @method _clear
     * @param e {Object} The event object.
     * @protected
     */
    _clear: function() {
        this.set(CURRENT_SEARCH_STRING, '');
        this.set(ERROR, '');
        this.set(RESULTS, []);
        this.set(BATCHES, null);
        this.set(BATCH_COUNT, null);
        this.set(SELECTED_BATCH, 0);
        this.set(CURRENT_FILTER_VALUE, null);
        this._search_input.set('value', '');
        this._results_box.set('innerHTML', '');
        this._filter_box.set('innerHTML', '');
    },

    /**
     * Handle clicks on the 'Search' button or entering the enter key in the
     * search field.  This fires the search event.
     *
     * @method _defaultSearchUserAction
     * @param e {Event.Facade} An Event Facade object.
     * @private
     */
    _defaultSearchUserAction: function(e) {
        e.preventDefault();
        this.set(CURRENT_FILTER_VALUE, null);
        var search_string = Y.Lang.trim(this._search_input.get('value'));
        this._performSearch(search_string);
    },

    /**
     * Fires the search event after checking the search string and reseting
     * the relevant picker data.
     * search event.
     * @param search_string The search term.
     * @param filter_name The name of a filter to use to limit the results.
     */
    _performSearch: function(search_string, filter_name) {
        if (search_string.length < this.get(MIN_SEARCH_CHARS)) {
            var msg =  Y.substitute(
                "Please enter at least {min} characters.",
                {min: this.get(MIN_SEARCH_CHARS)});
            this.set(ERROR, msg);
        } else {
            // Reset the selected batch for new searches.
            var current_search_string = this.get(CURRENT_SEARCH_STRING);
            if (current_search_string !== search_string) {
                this.set(SELECTED_BATCH, 0);
            }
            this.set(CURRENT_SEARCH_STRING, search_string);
            this.fire(SEARCH, search_string, undefined, undefined,
                filter_name);
        }
    },

    /**
     * By default, the search event puts the widget in search mode. It also
     * clears the error, if there is any.
     *
     * @method _defaultSearch
     * @param e {Event.Facade} An Event Facade object.
     * @protected
     */
    _defaultSearch: function(e) {
        this.set(ERROR, null);
        this.set(SEARCH_MODE, true);
    },

    /**
     * By default, the cancel event just hides the widget, but you can
     * have it also cleared by setting clear_on_cancel to 'true'.
     *
     * @method _defaultCancel
     * @param e {Event.Facade} An Event Facade object.
     * @protected
     */
    _defaultCancel : function(e) {
        Picker.superclass._defaultCancel.apply(this, arguments);
        this.set(SEARCH_MODE, false);
        if ( this.get('clear_on_cancel') ) {
            this._clear();
        }
    },

    /**
     * By default, the save event clears and hides the widget, but you can
     * have it not cleared by setting clear_on_save to 'false'. The search
     * entered by the user is passed in the first details attribute of the
     * event.
     *
     * @method _defaultSave
     * @param e {Event.Facade} An Event Facade object.
     * @protected
     */
    _defaultSave : function(e) {
        this.hide();
        if ( this.get('clear_on_save') ) {
            this._clear();
        }
    },

    /**
     * By default, the select-batch event turns on search-mode.
     *
     * @method _defaultSelectBatch
     * @param e {Event.Facade} An Event Facade object.
     * @protected
     */
    _defaultSelectBatch: function(e) {
        this.set(SEARCH_MODE, true);
    }
    });

/**
 * Some constants.
 */
Picker.NAME = PICKER;
Picker.SAVE = SAVE;
Picker.SEARCH = SEARCH;

/**
 * The details index of the save result.
 *
 * @static
 * @property SAVE_RESULT
 */
Picker.SAVE_RESULT = 0;

/**
 * The details index of the search string.
 *
 * @static
 * @property SEARCH_STRING
 */
Picker.SEARCH_STRING = 0;

/**
 * The details index of the selected batch value.
 *
 * @static
 * @property SELECTED_BATCH_VALUE
 */
Picker.SELECTED_BATCH_VALUE = 1;


Picker.ATTRS = {
    /**
     * Whether or not the search box and result list should be cleared when
     * the save event is fired.
     *
     * @attribute clear_on_save
     * @type Boolean
     */
    clear_on_save: { value: true },

    /**
     * Whether or not the search box and result list should be cleared when
     * the cancel event is fired.
     *
     * @attribute clear_on_cancel
     * @type Boolean
     */
    clear_on_cancel: { value: false },

    /**
     * A CSS selector for the DOM element that will activate (show) the picker
     * once clicked.
     *
     * @attribute picker_activator
     * @type String
     */
    picker_activator: { value: null },

    /**
     * An extra CSS class to be added to the picker_activator, generally used
     * to distinguish regular links from js-triggering ones.
     *
     * @attribute picker_activator_css_class
     * @type String
     */
    picker_activator_css_class: { value: 'js-action' },

    /**
     * Minimum number of characters that need to be entered in the search
     * string input before a search event will be fired. The search string
     * will be trimmed before testing the length.
     *
     * @attribute min_search_chars
     * @type Integer
     */
    min_search_chars: { value: 3 },

    /**
     * The current search string, which is needed when clicking on a different
     * batch if the search input has been modified.
     *
     * @attribute current_search_string
     * @type String
     */
    current_search_string: {value: ''},

    /**
     * The string representation of the current filter.
     *
     * @attribute current_filter_value
     * @type String
     */
    current_filter_value: {value: null},

    /**
     * A list of attribute name values used to construct the filtering options
     * for this picker..
     *
     * @attribute filter_options
     * @type Object
     */
    filter_options: {value: []},

    /**
     * The string representation of the value selected by using this picker.
     *
     * @attribute selected_value
     * @type String
     */
    selected_value: {value: null},

    /**
     * Meta information about the current state of the associated field,
     * whose value is selected by using this picker.
     *
     * @attribute selected_value_metadata
     * @type String
     */
    selected_value_metadata: {value: null},

    /**
     * Results currently displayed by the widget. Updating this value
     * automatically updates the display.
     *
     * @attribute results
     * @type Array
     */
    results: { value: [] },

    /**
     * This adds any form fields you want below the search field.
     * Updating this value automatically updates the display, but only
     * if the widget has already been rendered. Otherwise, the change
     * event never fires.
     *
     * @attribute search_slot
     * @type Node
     */
    search_slot: {value: null},

    /**
     * A place for custom html at the bottom of the widget. When there
     * are no search results the search_slot and the footer_slot are
     * right next to each other.
     * Updating this value automatically updates the display, but only
     * if the widget has already been rendered. Otherwise, the change
     * event never fires.
     *
     * @attribute footer_slot
     * @type Node
     */
    footer_slot: {value: null},

    /**
     * Batches currently displayed in the widget, which can be
     * clicked to change the batch of results being displayed. Updating
     * this value automatically updates the display.
     *
     * This an array of object containing the two keys, name (used as
     * the batch label) and value (used as additional details to SEARCH
     * event).
     *
     * @attribute batches
     * @type Array
     */
    batches: {value: null},

    /**
     * For simplified batch creation, you can set this to the number of
     * batches in the search results.  In this case, the batch labels
     * and values are automatically calculated.  The batch name (used as the
     * batch label) will be the batch number starting from 1.  The batch value
     * (used as additional details to the SEARCH event) will be the batch
     * number, starting from zero.
     *
     * If 'batches' is set (see above), batch_count is ignored.
     *
     * @attribute batch_count
     * @type Integer
     */
    batch_count: {value: null},

    /**
     * Batch currently selected.
     *
     * @attribute selected_batch
     * @type Integer
     */
    selected_batch: {
        value: 0,
        getter: function (value) {
            return value || 0;
        },
        validator: function (value) {
            var batches = this._getBatches();
            return Y.Lang.isNumber(value) &&
                   value >= 0 &&
                   value < batches.length;
        }},

    /**
     * Flag indicating if the widget is currently in search mode (so users
     * has triggered a search and we are waiting for results.)
     *
     * @attribute search_mode
     * @type Boolean
     */
    search_mode: { value: false },

    /**
     * The current error message. This puts the widget in 'error-mode',
     * setting this value to null clears that state.
     *
     * @attribute error
     * @type String
     */
    error: { value: null },

    /**
     * The message to display when the search returned no results. This string
     * can contain a 'query' placeholder
     *
     * @attribute no_results_search_message
     * @type String
     * @default No items matched "{query}".
     */
    no_results_search_message: {
        value: 'No items matched "{query}".'
    }
};


/**
 * This plugin is used to associate a picker instance to an input element of
 * the DOM.  When the picker is shown, it takes its initial value from that
 * element and when the save event is fired, the value of the chosen item
 * (from the picker's list of results) is copied to that element.
 *
 * Also, this plugin expects a single attribute (input_element) in the
 * config passed to its constructor, which defines the element that will be
 * associated with the picker.
 *
 * @class TextFieldPickerPlugin
 * @extends Y.Plugin.Base
 * @constructor
 */

function TextFieldPickerPlugin(config) {
    TextFieldPickerPlugin.superclass.constructor.apply(this, arguments);
}

TextFieldPickerPlugin.NAME = 'TextFieldPickerPlugin';
TextFieldPickerPlugin.NS = 'txtpicker';

Y.extend(TextFieldPickerPlugin, Y.Plugin.Base, {
    initializer: function(config) {
        var input = Y.one(config.input_element);
        this.doAfter('save', function (e) {
            var result = e.details[Picker.SAVE_RESULT];
            this.get('host').set(SELECTED_VALUE_METADATA, result.metadata);
            this.get('host').set(SELECTED_VALUE, result.value);
            input.set("value",  result.value || '');
            // If the search input isn't blurred before it is focused,
            // then the I-beam disappears.
            input.blur();
            input.focus();
        });
        this.doAfter('show', function() {
            var selected_value = null;
            if ( input.get("value") ) {
                selected_value = input.get("value");
            }
            this.get('host')._search_input.set('value', selected_value);
            this.get('host').set(SELECTED_VALUE, selected_value);
        });
    }
});

var namespace = Y.namespace('lazr.picker');
namespace.Picker = Picker;
namespace.TextFieldPickerPlugin = TextFieldPickerPlugin;

}, "0.1", {"skinnable": true,
           "requires": ["oop", "escape", "event", "event-focus", "node",
                        "plugin", "substitute", "widget", "widget-stdmod",
                        "lazr.overlay", "lp.anim", "lazr.base",
                        "lp.app.widgets.expander"]
});
