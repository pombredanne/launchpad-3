/* Copyright Canonical Ltd. 2006-2007.  All rights reserved.
Authors: Guido Wesdorp, Steve Alexander
*/

function ensure_units(value) {
    return (parseInt(value) == value) ? value + 'px' : value;
};

function select_element_and_parents(element) {
    addElementClass(element, 'selected');
    var curr = element.parent_menu;
    while (curr) {
        addElementClass(curr, 'selected');
        curr = curr.parent_menu;
    };
};

function unselect_element_and_parents(element) {
    removeElementClass(element, 'selected');
    var curr = element.parent_menu;
    while (curr) {
        removeElementClass(curr, 'selected');
        curr = curr.parent_menu;
    };
};

function unselect_element_and_children(element) {
    elements = getElementsByTagAndClassName('li', 'selected', parent=element)
    for (var i=0; i < elements.length; i++) {
        removeElementClass(elements[i], 'selected');
    };
};

function lognode(message, el) {
    if (el) {
        log(message + ': ' +
            getFirstElementByTagAndClassName('a', null, parent=el).innerHTML);
    } else {
        log(message + ': null');
    };
};

window.lpmenu = new function() {
    var lpmenu = this;

    // some config vars, set before calling lpmenu.initialize()
    this.TOP_MENU_DELAY = 0.9;
    this.MENU_DELAY = 0.1;
    this.MENU_OUT_DELAY = 2.0; // set to 0 to disable
    this.NOT_ENTERED_MENU_DELAY = 4.0;
    this.SCROLL_DELAY = 0.17;

    this.CLOSE_ON_CLICK = true;
    this.CLOSE_ON_ESCAPE = true;

    this.MINWIDTH = 70;

    this.IE_TOP_CORRECTION = '-0.52em';
    this.IE_OFFSET_CORRECTION = 20;

    this.LEFT_CORRECTION = 2;

    this.LOCATION_BAR_HEIGHT = 26;

    this.Loader = Loader = function(url) {
        if (url) {
            this.initialize(url);
        };
    };

    Loader.prototype.initialize = function(url) {
        this.url = url;
        this._sub_cache = {};
    };

    Loader.prototype.preload_from_html = function(preloadel) {
        /* 'preload' menus from the document

            preloadel should be an element with div childnodes, each
            of which have an 'lpm:mid' attribute with the id of the menu
            they contain

            the menus will be stored in the sub_cache and when done the
            preloadel will be removed from the document
        */
        for (var i=0; i < preloadel.childNodes.length; i++) {
            if (preloadel.childNodes[i].nodeType != 1) {
                continue;
            };
            var child = preloadel.childNodes[i];
            var mid = lpmenu.get_mid(child);
            this._sub_cache[mid] = child;
        };
        preloadel.parentNode.removeChild(preloadel);
    };

    Loader.prototype.preload = function(mid) {
        this.load(mid);
    };

    var current_deferred = null;
    Loader.prototype.load = function(mid, handler) {
        /* get a submenu representation from the server 

            mid is the menu-id of the item clicked

            the server should return an HTML fragment with the 
            following structure:

              <div class="menu">
                <div class="item" lpm:mid="[mid]">
                    [html]
                </div>
                ...
              </div>

            where [mid] is the menu-id of the sub-element (which can
            later be used to load the contents for that sub-element),
            and [html] a snippet of (well-formed) HTML containing a link
            (if desired) and some text to display

            in certain cases it may be desired to return more data than 
            requested from the server, in that case embed all the submenus
            in a larger div with the attribute 'lpm:container' set to true,
            and make sure all the contained divs (the sub menus) have an
            'lpm:mid' attribute defined (one of which must obviously be the
            requested mid)

            may do caching of menu contents by id

            when done (optional) handler will be called with the sub menu
            as its only argument
        */
        // if there's a handler (so we're not preloading anything) and there's
        // already a menu load action in progress, cancel it
        if (handler && current_deferred) {
            current_deferred.cancel();
            current_deferred = null;
        };

        // check our cache, if we already have the element cached use that
        if (this._sub_cache[mid]) {
            if (handler) {
                handler(this._sub_cache[mid]);
            };
            return;
        };

        var self = this;
        var ihandler = function(req) {
            // if a mouseout has occurred since the request was made, don't
            // do anything here, we have to display another menu in that case
            if (!self.continue_load) {
                return;
            };
            if (req.status != 200 && req.status != 304) {
                log('ALERT: problem loading data: ' + req.status);
                return;
            };
            // nasty hack: since the return value is HTML, not XML,
            // req.responseXML is not available, we have to 'create
            // it ourselves'...
            var div = document.createElement('div');
            div.innerHTML = req.responseText;
            var rootel = div.childNodes[0];

            // see if we get back more than we requested, if so store 
            // everything in cache (but call the handler only with the
            // requested sub)
            var sub = null;
            var iscontainer = rootel.getAttribute('lpm:container');
            var subs = [];
            if (iscontainer) {
                for (var i=0; i < rootel.childNodes.length; i++) {
                    var child = rootel.childNodes[i];
                    if (child.nodeType != 1) {
                        continue;
                    };
                    var submid = lpmenu.get_mid(child);
                    if (submid) {
                        self._sub_cache[submid] = child;
                    };
                    if (submid == mid) {
                        sub = child;
                    };
                };
                if (!sub) {
                    log('ALERT: problem loading data from server: requested menu ' +
                          'not in the response! please contact your server ' +
                          'administrator');
                    return;
                };
            } else {
                sub = rootel;
                self._sub_cache[mid] = sub;
            };
            if (handler) {
                handler(sub);
            };
        };
        // set a flag here so we can interrupt the loading (by setting it to
        // false (see LPMenu.mouse_out_handler())
        this.continue_load = true;
        var d = MochiKit.Async.doSimpleXMLHttpRequest(mid);
        d.addCallbacks(ihandler, this.errback);
        // if there's no handler, we don't want this to be cancelled on a new
        // request (as we're dealing with a preload request)
        // XXX SteveA 2006-05-31:
        // note that this can potentially cause a URL to get requested
        // twice in a row; let's hope HTTP caching helps us here, if not 
        // perhaps we have to change this a bit...
        if (handler) {
            current_deferred = d;
        };
    };

    Loader.prototype.errback = function(err) {
        /* deferred error handling: alert when errors while loading */
        // XXX SteveA 2006-05-31:
        // In a bit of a hurry now, obviously this needs to be done
        // differently
        if (err.toString().indexOf('CancelledError') > -1) {
            return;
        };
        log('ALERT: An error occurred when loading a menu item from the ' +
                'server: ' + err);
    };

    this.LPMenu = LPMenu = function(rootel, loader, lineheight, 
                                    iconwidth, firstlineempty) {
        /* LaunchPad dynamic menu code */
        if (rootel !== null) {
            this.initialize(rootel, loader, lineheight, iconwidth, 
                                firstlineempty);
        };
    };

    // closure used below and in update method
    var escape_clicked = false;
    LPMenu.prototype.initialize = function(rootel, loader, lineheight, 
                                            iconwidth, firstlineempty) {
        /* initialize the menu

            rootelid is the id of an element to attach the menu to

            menuurl is the url to load menu-data (currently HTML)
            from: currently the code expects a script to be available
            that groks a single query arg 'menuid', which is the id
            of the menu to display

            lineheight is the CSS value used as line-height for the
            menu items (e.g. '1.8em', default '2em')

            firstlineempty determines whether it's allowed to place items
            on the first line of the page (set to false when using a menu
            on the top of the page)
        */
        this.rootel = rootel;
        if (lpmenu.CLOSE_ON_CLICK) {
            MochiKit.Signal.connect(rootel.ownerDocument, 'onmousedown', 
                                    this, this.close_all);
        };
        if (lpmenu.CLOSE_ON_ESCAPE) {
            var self = this;
            MochiKit.Signal.connect(document, 'onkeypress',
                function(e) {
                    if (e.event().keyCode == 27) {
                        escape_clicked = true;
                        self.close_all(e);
                    };
                }
            );
        };
        this.loader = loader;
        this.open = false;

        // get a height per item calculated
        if (!lineheight) {
            lineheight = '2em';
        };
        this.lineheight = lineheight;
        this.pixelHeight = Math.ceil(this._get_pixel_height(this.rootel, 
                                        lineheight));

        this.firstlineempty = firstlineempty;
        this.iconWidth = iconwidth;

        var sub = this.prepare_menu_items(null, rootel); // no parent
        // have to replace here because the rendered version is a clone of
        // the displayed one
        var rendered = sub.get_rendered();
        rootel.parentNode.replaceChild(rendered, rootel);
        this.rootel = rendered;
    };

    LPMenu.prototype._get_pixel_height = function(el, lineheight) {
        /* some trickery to get the height in pixels for a single menu item */
        el.style.lineHeight = ensure_units(lineheight);
        el.style.height = ensure_units(lineheight);
        var cs = lpmenu.getComputedStyle(el);
        if (cs) {
            return parseFloat(cs.height);
        } else {
            return parseFloat(el.style.pixelHeight);
        };
    };

    LPMenu.prototype.prepare_menu_items = function(menu, sub) {
        /* adds event handlers to a menu item */
        return new LPSubMenu(sub, menu, this);
    };

    var current_mouse_over_deferred = null;
    var current_mouse_out_target = null;
    LPMenu.prototype.mouse_over_handler = function(event, el) {
        if (event.relatedTarget() == null) {
            // Mouse ended up floating over here on a page load.
            // So set a much longer delay.
            var delay = lpmenu.NOT_ENTERED_MENU_DELAY;
        } else {
            var delay = this.get_delay(el);
        };
        /* open a submenu (if appropriate) */
        var target = el;
        //event.stop();
        if (current_mouse_over_deferred) {
            current_mouse_over_deferred.cancel();
            current_mouse_over_deferred = null;
        };
        // if the sub menu is already displayed, return
        if (el.sub) {
            // This is kind of a hack.
            // We really need separate concepts of "mouse enters submenu"
            // and "mouse enters menu item".  Right now, these things are
            // confused, as when the mouse goes from a menu item to its
            // submenu, the mouse doesn't technically *leave* the menu
            // item, because they're nested.
            // So, here, if the submenu is already displayed, ensure that
            // its items are not selected, and clear the
            // current_mouse_out_target so that a subsequent mouse-over
            // the submenu will work properly.
            unselect_element_and_children(el.sub);
            if (current_mouse_out_target == el) {
                current_mouse_out_target = null;
            };
            return;
        };

        var self = this;

        current_mouse_over_deferred = MochiKit.Async.callLater(
            delay,
            function() {
                try {
                    // If we're moving back into what we last moved out of,
                    // update the tree as if we moved from outside the menus.
                    if (current_mouse_out_target == el) {
                        self.update_tree(self.rootel, el);
                    } else {
                        self.update_tree(current_mouse_out_target, el);
                    };
                } catch(e) {
                    log('exception in update_tree 1: ' + e.message);
                };
                current_mouse_out_target = null;

                self.open = true;
            }
        );
    };

    LPMenu.prototype.mouse_out_handler = function(event, el) {
        /* close the element we're moving out of (if appropriate) */
        // XXX SteveA 2006-05-31:
        // Mouse out handling is very messy in browsers... 
        // it's not always clear what the 'related target' (the target
        // to which the mouse pointed moves) is set to when moving
        // away from a target... therefore this method is a bit longish,
        // and contains some defensive code...

        // if we're already loading another menu, cancel that
        this.loader.continue_load = false;

        // first let's cancel any bubbling...
        // there is none, as we're using mouse_leave from mochikit
        //event.stopPropagation();

        // also we find the element moved to
        var movedto = event.relatedTarget();

        if (!movedto) {
            // we don't have a movedto, use the body (which makes that all
            // menus are closed, basically)
            movedto = document.getElementsByTagName('body')[0];
        } else if (movedto.nodeType == 3) {
            // konqueror returns the child text node
            movedto = movedto.parentNode;
        };

        // when moving to an anchor node, that instead of the menu item will
        // be the movedto (since that catches onmouseover), if so walk up to 
        // parent
        while (movedto.nodeName.toLowerCase() == 'a') {
            movedto = movedto.parentNode;
        };

        // in some cases this is the same, if so we ignore the
        // event (because things seem to stay the same)
        if (el == movedto) {
            return;
        };
        if (!current_mouse_out_target) {
            current_mouse_out_target = el;
        };
        // XXX SteveA 2006-05-31:
        // Close on document mouse over instead?
        if (!this._in_menu(movedto)) {
            // the user has moved out of the tree, so no mouse over event
            // is registered... to make sure submenus are closed anyway,
            // we start a deferred of our own
            var self = this;
            var close_path_handler = function() {
                if (current_mouse_out_target) {
                    self.close_path(current_mouse_out_target, movedto);
                    current_mouse_out_target = null;
                    current_selected = null;
                };
            };
            if (current_mouse_over_deferred) {
                current_mouse_over_deferred.cancel();
                current_mouse_over_deferred = null;
            };

            if (lpmenu.MENU_OUT_DELAY) {
                current_mouse_over_deferred = MochiKit.Async.callLater(
                    lpmenu.MENU_OUT_DELAY,
                    close_path_handler
                );
            };
        };
    };

    var current_selected = null;
    LPMenu.prototype.update_tree = function(movedfrom, movedto) {
        if (movedfrom) {
            this.close_path(movedfrom, movedto);
        };
        if (escape_clicked) {
            return;
        };
        var mid = lpmenu.get_mid(movedto);
        var self = this;
        if (mid) {
            this.loader.load(
                mid,
                function(sub) {
                    self.attach(movedto, sub);
                }
            );
        };
        if (movedfrom != movedto) {
            if (current_selected) {
                unselect_element_and_parents(current_selected);
                if (current_selected != movedfrom && movedfrom) {
                    unselect_element_and_parents(movedfrom);
                };
            };
            current_selected = movedto;
            select_element_and_parents(current_selected);
        };
    };

    LPMenu.prototype.attach = function(parent, sub) {
        /* attach a sub menu to a parent element 

            make sure event handlers are attached
        */
        var submenu = this.prepare_menu_items(parent, sub);
        var rendered = submenu.get_rendered();
        parent.sub = rendered

        parent.appendChild(rendered);
        submenu.update_item_widths();

        // Check whether we need to adjust the new menu's position to keep
        // it on the page.
        var cs = lpmenu.getComputedStyle(rendered);
        if (cs) {
            var menuheight = parseInt(cs.height);
        } else {
            var menuheight = rendered.offsetHeight;
        };
        var offset_top_parent = getElementPosition(parent).y;
        if (offset_top_parent + menuheight > lpmenu.getAvailHeight()) {
            if (document.all) {
                rendered.style.marginTop = ensure_units(
                    -(offset_top_parent - lpmenu.IE_OFFSET_CORRECTION));
            } else {
                rendered.style.top = ensure_units(
                    this.firstlineempty ? this.lineheight : '0px');
            };
        };
    };

    LPMenu.prototype.close_all = function(event) {
        if (escape_clicked) {
            current_mouse_out_target = current_selected;
            escape_clicked = false;
        };
        if (current_mouse_out_target) {
            event.stop();
            var body = this.rootel.ownerDocument.getElementsByTagName(
                                                                'body')[0];
            this.update_tree(current_mouse_out_target, body);
        };
        this.open = false;
    };

    LPMenu.prototype.close_path = function(movedfrom, movedto) {
        // now let's see if the element we moved to is not a child of
        // the one we moved from, if it isn't we close any open sub menus
        if (!this._ischild(movedto, movedfrom)) {
            if (movedfrom.sub) {
                movedfrom.removeChild(movedfrom.sub);
                movedfrom.sub = null;
            };
            // also, if the element we moved to is not movedfrom's sibling, nor 
            // a sibling of its parent, close everything we can
            if (!this._issibling(movedfrom, movedto) && 
                    (!movedfrom.parent_menu || 
                        !this._isparent(movedto, movedfrom))) {
                var current = movedfrom;
                while (current && 
                        !this._issibling(current, 
                            movedto.parentNode.parentNode) &&
                        current != this.rootel.parentNode) {
                    if (current.sub) {
                        current.sub.parentNode.removeChild(current.sub);
                        current.sub = null;
                    };
                    removeElementClass(current, 'selected');
                    if (current.parentNode) {
                        current = current.parentNode.parentNode;
                    } else {
                        current = current.parent_menu;
                    };
                };
            };
        };
    };

    LPMenu.prototype.get_delay = function(el) {
        if (el.parentNode == this.rootel && !this.open) {
            return lpmenu.TOP_MENU_DELAY;
        } else {
            return lpmenu.MENU_DELAY;
        };
    };

    // some checker functions used by mouse_out_handler()
    LPMenu.prototype._issibling = function(el1, el2) {
        try {
            return (el1 && el2 && el1.parentNode && el2.parentNode && 
                    el1.parentNode.parentNode &&
                    el1.parentNode.parentNode == el2.parentNode.parentNode);
        } catch(e) {
            log('exception in LPMenu._issibling(): ' + e.message);
        };
    };

    LPMenu.prototype._isparent = function(el1, el2) {
        try {
            if (el2.parentNode) {
                var parent = el2.parentNode.parentNode;
            } else {
                var parent = el2.parent_menu;
            };
            if (el1 == parent) {
                return true;
            };
            return false;
        } catch(e) {
            log('exception in LPMenu._isparent(): ' + e.message);
        };
    };

    LPMenu.prototype._ischild = function(el1, el2) {
        /* returns true if either el1 itself or el1's parent is
            a child node of el2
        */
        try {
            var parent = el1.parentNode;
            for (var i=0; i < el2.childNodes.length; i++) {
                var child = el2.childNodes[i];
                if (child == parent) {
                    return true;
                };
            };
            return false;
        } catch(e) {
            log('exception in LPMenu._ischild(): ' + e.message);
        };
    };

    LPMenu.prototype._in_menu = function(el) {
        /* check whether an element is inside the menu */
        var current = el;
        while (current && current.parentNode && 
                current.parentNode.nodeName.toLowerCase() != 'body') {
            if (current == this.rootel) {
                return true;
            };
            current = current.parentNode;
        };
        return false;
    };

    this.LPSubMenu = LPSubMenu = function(subel, parent, root) {
        if (subel !== null) {
            this.initialize(subel, parent, root);
        };
    };

    LPSubMenu.prototype.initialize = function(subel, parent, root) {
        this.org_subel = subel;
        this.subel = subel.cloneNode(true);
        this.subel.org = this.subel;

        this.parent = parent; 
        this.root = root;
        // only filled when the menu is too big for the screen
        this.items = null; 
        this.offset = 0;

        if (parent && parent.parentNode.parentNode.nodeName == 'LI') {
            if (document.all) {
                this.subel.style.marginLeft = '0px';
                this.subel.style.marginTop = ensure_units(
                    lpmenu.IE_TOP_CORRECTION);
                if (this.subel.parentNode != this.root.rootel) {
                    this.subel.style.left = ensure_units(
                        parent.parentNode.maxWidth + this.root.iconWidth);
                };
            } else {
                this.subel.style.left = ensure_units(
                    getElementDimensions(parent.parentNode).w
                    - lpmenu.LEFT_CORRECTION
                    );
                var inneranchor = parent.getElementsByTagName('a')[0];
                this.subel.style.top = ensure_units(
                    getElementPosition(inneranchor).y -
                    getElementPosition(parent.parentNode).y)
                this.subel.parentitem = parent;
            };
        } else if (document.all && parent) {
            // locate the first sub menus (below the root items)
            this.subel.style.left = ensure_units(parent.offsetLeft);
            this.subel.style.posTop = ensure_units(this.root.lineheight);
            this.subel.style.top = ensure_units(this.root.lineheight);
            this.subel.set_root_top = this.root.lineheight;
        } else {
            // Override position of top level menus
            if (this.parent) {
                var inneranchor = this.parent.getElementsByTagName('a')[0];
                var inneranchorpos = getElementPosition(inneranchor);
                this.subel.style.left = ensure_units(inneranchorpos.x);
                this.subel.style.top = ensure_units(
                    inneranchorpos.y + lpmenu.LOCATION_BAR_HEIGHT - 1);
            };
        };

        var parent = parent ? parent.parentNode : root.rootel;
        this.maxWidth = subel.maxWidth || this._get_max_width(subel, parent);
        if (this.maxWidth < lpmenu.MINWIDTH) {
            this.maxWidth = lpmenu.MINWIDTH;
        };
        this.subel.maxWidth = subel.maxWidth = this.maxWidth;

        // set the handlers, note that we don't have the loop in the 
        // set_handlers function because that seems to mess up the closure
        if (!this.subel.handlers_set) {
            for (var i=0; i < this.subel.childNodes.length; i++) {
                // XXX SteveA 2006-05-31
                // Currently we do caching in the loader, which means that
                // we might get DOM nodes that have already been used before,
                // in that case we don't set the handlers again... we might
                // want to cache LPSubMenus in the future though, avoiding this
                // (and probably some other) issue(s)
                var el = this.subel.childNodes[i];
                if (el.nodeType != 1) {
                    continue;
                };
                this.set_handlers(el);

                // See if we already have this menu item's submenu visible.
                // If so, make the item not a container, and not have a submenu.
                var menuid = getNodeAttribute(el, 'lpm:mid');
                if (menuid != null) {
                    var curr = el.parent_menu;
                    while (curr) {
                        if (menuid == lpmenu.get_mid(curr)) {
                            setNodeAttribute(el, 'lpm:mid', null);
                            removeElementClass(
                                getFirstElementByTagAndClassName('a', null, parent=el),
                                'container');
                            break;
                        };
                        curr = curr.parent_menu;
                    };
                };
            };
            this.subel.handlers_set = true;
        };

        this.menu = this.render_as_menu(this.subel);
    }

    LPSubMenu.prototype.set_handlers = function(el) {
        /* set the mouseover and mouseout handlers for the element */
        var overhandler = function(e) {
            e.stopPropagation();
            this.root.mouse_over_handler(e, el);
        };
        MochiKit.Signal.connect(el, 'onmouseover', this, overhandler);
        var outhandler = function(e) {
            //e.stop();
            this.root.mouse_out_handler(e, el);
        };
        MochiKit.Signal.connect(el, 'onmouseleave', this, outhandler);
        var clickhandler = function(e) {
            this.root.loader.continue_load = false;
        };
        MochiKit.Signal.connect(el, 'onclick', this, clickhandler);
        el.parent_menu = this.parent;
    };

    LPSubMenu.prototype.render_as_menu = function(subel) {
        /* convert the full list of elements to what should be presented

            may return the subel element as-is, but may also return a
            formatted version with scroll bars, and may move the menu up
            to the top of the document if required
        */
        if (this.items) {
            return this._render_scrolled_menu();
        };

        var items = [];
        for (var i=0; i < subel.childNodes.length; i++) {
            if (subel.childNodes[i].nodeType == 1) {
                items.push(subel.childNodes[i]);
            };
        };
        // store the list of items on 'this' for later use
        this.items = items;

        // set classes to help styling
        if (this.items.length > 0) {
            addElementClass(this.items[0], 'first');
            addElementClass(this.items[this.items.length-1], 'last');
        };

        var menuheight = Math.ceil(items.length * this.root.pixelHeight);
        var availHeight = lpmenu.getAvailHeight();
        if (this.root.firstlineempty) {
            availHeight -= this.root.pixelHeight;
        };
        if (menuheight <= lpmenu.getAvailHeight()) {
            // we can return the sub el as-is, no scrolling necessary...
            return subel;
        };

        this.max_visible = Math.floor(parseInt(lpmenu.getAvailHeight()) / 
                                        this.root.pixelHeight);
        if (this.root.firstlineempty) {
            this.max_visible--;
        };
        return this._render_scrolled_menu();
    };

    LPSubMenu.prototype._render_scrolled_menu = function() {
        // XXX SteveA 2006-05-31:
        // I'd rather use this.subel.ownerDocument here, but for some
        // reason IE doesn't seem to like that...
        var doc = document;
        var items = this.items;
        var show_top_button = this.offset > 0;
        var show_bottom_button = this.offset + this.max_visible < items.length;
        var num_to_show = this.max_visible;

        if (show_top_button) {
            num_to_show -= 1;
        };
        if (show_bottom_button) {
            num_to_show -= 1;
        };

        var menuitems = items.slice(this.offset, this.offset + num_to_show);
        this.menuitems = menuitems;

        if (show_top_button) {
            var topbutton = this.create_scroll_button('up');
            menuitems.unshift(topbutton);
        };

        if (show_bottom_button) {
            var bottombutton = this.create_scroll_button('down');
            menuitems.push(bottombutton);
        };

        var clone = this.subel.cloneNode(false); // not deep!
        clone.org = this.subel;
        addElementClass(clone, 'scrolled');
        clone.maxWidth = this.subel.maxWidth;
        for (var i=0; i < this.max_visible; i++) {
            clone.appendChild(menuitems[i + this.offset]);
        };

        clone.style.position = 'absolute';
        if (!document.all) {
            clone.style.top = ensure_units(
                this.root.firstlineempty ? this.root.lineheight : '0px');
        };
        return clone;
    };

    var scrolling_stopped = null;
    LPSubMenu.prototype.start_scroll_down = function(e) {
        scrolling_stopped = false;
        try {
            this.root.update_tree(current_mouse_out_target, e.target());
        } catch(e) {
            log('error in update tree 2: ' + e.message);
        };
        this.scroll_down();
    };

    LPSubMenu.prototype.start_scroll_up = function(e) {
        scrolling_stopped = false;
        try {
            this.root.update_tree(current_mouse_out_target, e.target());
        } catch(e) {
            log('error in update tree 3: ' + e.message);
        };
        this.scroll_up();
    };

    var scroll_deferred = null;
    LPSubMenu.prototype.scroll_down = function() {
        if (current_mouse_over_deferred) {
            current_mouse_over_deferred.cancel();
            current_mouse_over_deferred = null;
        };

        if (scrolling_stopped) {
            return;
        };
        try {
            this.adjust_menu(+1);
        } catch(e) {
            log('exception in adjust_menu: ' + e.message);
        };
        var self = this;
        scroll_deferred = MochiKit.Async.callLater(
            lpmenu.SCROLL_DELAY,
            function() {
                self.scroll_down();
            }
        );
    };

    LPSubMenu.prototype.scroll_up = function() {
        if (current_mouse_over_deferred) {
            current_mouse_over_deferred.cancel();
            current_mouse_over_deferred = null;
        };

        if (scrolling_stopped) {
            return;
        };
        try {
            this.adjust_menu(-1);
        } catch(e) {
            log('exception in adjust_menu: ' + e.message);
        };
        var self = this;
        scroll_deferred = MochiKit.Async.callLater(
            lpmenu.SCROLL_DELAY,
            function() {
                self.scroll_up();
            }
        );
    };

    LPSubMenu.prototype.stop_scroll = function() {
        try {
            scroll_deferred.cancel();
        } catch(e) {
            log('exception during cancellation of deferred: ' + e.message);
        };
        scrolling_stopped = true;
    };

    LPSubMenu.prototype.adjust_menu = function(direction) {
        // XXX SteveA 2006-05-31:
        // Not very optimal, some code duplication and such.
        var items = this.items;
        var top_button_shown = this.menu.childNodes[0].isbutton;
        var bottom_button_shown = this.menu.childNodes[
            this.menu.childNodes.length - 1
        ].isbutton;
        var num_to_show = this.max_visible;

        if (top_button_shown) {
            // last item is button
            num_to_show -= 1;
        };
        if (bottom_button_shown) {
            num_to_show -= 1;
        };

        this.offset += direction;
        var show_top_button = this.offset > 0;
        var show_bottom_button = this.offset + this.max_visible < items.length;

        if (direction > 0) {
            // scroll down, remove the first item and add a new one on the
            // bottom
            var firstitem = this.menu.childNodes[1];
            if (!top_button_shown) {
                // the top button is not yet shown, but we're scrolling down
                // now so we have to show it... 
                var scrollbutton = this.create_scroll_button('up');
                this.menu.replaceChild(
                    scrollbutton,
                    this.menu.childNodes[0]
                );
            };
            this.menu.removeChild(
                firstitem
            );
            var scrollbutton = this.menu.childNodes[
                this.menu.childNodes.length - 1
            ];
            var curritems = this.menu.childNodes.length;
            scrollbutton.parentNode.insertBefore(
                this.items[this.offset + this.max_visible - 2],
                scrollbutton
            );
            // see if we have to replace the scroll button with the last
            // item in the lisvisible
            if (this.offset + this.max_visible >= this.items.length) {
                scrollbutton.parentNode.replaceChild(
                    this.items[this.items.length - 1],
                    scrollbutton
                );
                this.stop_scroll();
            };
        } else {
            // scroll up, add an item on top and remove one from the bottom,
            // if there's not yet a scroll button we replace yet another item
            // from the bottom with a new button

            if (!bottom_button_shown) {
                // add scroll button
                var scrollbutton = this.create_scroll_button('down');
                this.menu.replaceChild(
                    scrollbutton,
                    this.menu.childNodes[this.menu.childNodes.length - 1]
                );
            };
            // remove an item on the bottom (before the scroll button)
            this.menu.removeChild(
                this.menu.childNodes[this.menu.childNodes.length - 2]
            );
            // add a new item on top (before the scroll button)
            this.menu.insertBefore(
                this.items[this.offset + 1],
                this.menu.childNodes[1]
            );
            if (this.offset == 0) {
                this.stop_scroll();
                var self = this;
                MochiKit.Async.callLater(
                    0,
                    function() {
                        var scrollbutton = self.menu.childNodes[0];
                        self.menu.replaceChild(
                            self.items[0],
                            scrollbutton
                        );
                        self.update_item_widths();
                    }
                );
            };
        };
        this.update_item_widths();
    };

    LPSubMenu.prototype.get_rendered = function() {
        return this.menu;
    };

    LPSubMenu.prototype.create_scroll_button = function(direction) {
        /* create a scroll button

            direction can be 'up' or 'down' (string)
        */
        var el = this.items[0].cloneNode(false);
        el.removeAttribute('lpm:mid');
        el.removeAttribute('lpm:midpart');
        addElementClass(el, 'scrollbutton');
        addElementClass(el, direction);
        el.appendChild(document.createTextNode('\xa0'));
        el.isbutton = true;
        MochiKit.Signal.connect(el, 'onmouseover', this, 
                                    this['start_scroll_' + direction]);
        MochiKit.Signal.connect(el, 'onmouseout', this,
                                    this.stop_scroll);
        return el;
    };

    LPSubMenu.prototype.update_item_widths = function() {
        // store the found value on the submenu and make it adjust its items
        for (var i=0; i < this.menu.childNodes.length; i++) {
            var child = this.menu.childNodes[i];
            if (child.nodeType != 1 || child.nodeName.toLowerCase() != 'li') {
                continue;
            };
            child.style.width = ensure_units(
                this.maxWidth + this.root.iconWidth);
        };
    };

    LPSubMenu.prototype._get_max_width = function(subel, parent) {
        // determine width of the largest item
        var maxwidth = 0;
        // the item to check the width of must be rendered already, so we
        // create a clone and walk through its items, temporarily attaching
        // each on to the document somewhere
        var clone = subel.cloneNode(true);
        clone.org = subel;
        while (clone.childNodes.length > 0) {
            var child = clone.firstChild;
            if (child.nodeType != 1) {
                clone.removeChild(child);
                continue;
            };
            if (document.all) {
                // XXX SteveA 2006-05-31:
                // IE suX0rZ
                child.style.display = 'inline';
            };
            if (parent.org) parent = parent.org;
            parent.appendChild(child);
            var cs = lpmenu.getComputedStyle(child);
            if (cs) {
                var width = parseInt(cs.width);
            } else {
                var width = child.offsetWidth;
            };
            child.parentNode.removeChild(child);
            if (width > maxwidth) {
                maxwidth = width;
            };
        };
        // we're done with the clone, throw it away
        //clone.parentNode.removeChild(clone);
        return maxwidth;
    };

    this.get_mid = function(el) {
        /* get the menu id

            this is either retrieved from an item attribute as-is or calculated 
            by combining an attribute of the parent and one of itself
        */
        var full_mid = el.getAttribute('lpm:mid');
        if (full_mid) {
            return full_mid;
        };
        var part_mid = el.getAttribute('lpm:midpart');
        if (!part_mid) {
            return undefined;
        };
        var parent_mid = el.parentNode.getAttribute('lpm:midbase');
        if (!parent_mid) {
            throw('Child has partial mid ' + part_mid + 
                    ', but parent doesn\'t have midbase defined');
        };
        var mid = parent_mid.replace('$$', part_mid);
        return mid;
    };

    this.getComputedStyle = function(el) {
        var doc = document;
        return (doc.defaultView && 
                    doc.defaultView.getComputedStyle(el, null));
    };

    this.getAvailHeight = function() {
        return window.innerHeight || 
                        document.getElementsByTagName('body')[0].clientHeight;
    };

    this.initialize = function(rootelids, menuurl, preloadelid, preloadlist,
                                lineheight, iconwidth, istopmenu) {
        /* initialze the code */
        // create a loader
        var loader = new lpmenu.Loader(menuurl);

        // preload data from the HTML
        loader.preload_from_html(document.getElementById(preloadelid));

        // preload data from the server (non-blocking)
        for (var i=0; i < preloadlist.length; i++) {
            loader.preload(preloadlist[i]);
        };

        var menus = [];
        for (var i=0; i < rootelids.length; i++) {
            var el = document.getElementById(rootelids[i]);
            menus.push(new lpmenu.LPMenu(el, loader, lineheight, iconwidth, 
                                            istopmenu));
        };

        return menus;
    };

    this.cleanup = function(menus) {
        /* should remove all DOM to JS references from the menus */
    };
}();
