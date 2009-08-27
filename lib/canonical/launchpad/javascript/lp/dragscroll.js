/*
 * Based on dragscroll script by Nicolas Mendoza <nicolasm@opera.com>.
 * http://people.opera.com/nicolasm/userjs/dragscroll
 */

/**
 * This class allows you to scroll a page by dragging it.
 *
 * @class DragScrollEventHandler
 * @constructor
 */
DragScrollEventHandler = function() {
    this.dragging = false;
    this.last_position = null;
}

DragScrollEventHandler.prototype = {
    /**
     * Add the event handlers and change the cursor to indicate
     * that drag scrolling is active.
     *
     * @method activate
     */
    activate: function() {
        document.addEventListener("mousedown", this._startDragScroll, false);
        document.addEventListener("mouseup", this._stopDragScroll, false);
        document.addEventListener("mouseout", this._stopDragScroll, false);
        document.addEventListener("mousemove", this._dragScroll, false);
        document.body.style.cursor = 'move';
    },

    /**
     * Remove the event handlers and change the cursor to indicate
     * that drag scrolling is inactive.
     *
     * @method deactivate
     */
    deactivate: function() {
        document.removeEventListener(
            "mousedown", this._startDragScroll, false);
        document.removeEventListener("mouseup", this._stopDragScroll, false);
        document.removeEventListener("mouseout", this._stopDragScroll, false);
        document.removeEventListener("mousemove", this._dragScroll, false);
        document.body.style.cursor = '';
    },

    /**
     * MouseDown event handler that causes _dragScroll to
     * take action when it receives a MouseMove event.
     *
     * @method _startDragScroll
     */
    _startDragScroll: function(e) {
        if (e.button == 0) {
            this.dragging = true;
            this.last_position = e;
        }
        e.preventDefault();
        e.stopPropagation();
    },

    /**
     * MouseUp & MouseOut event handler that causes _dragScroll to
     * once again ignore MouseMove events. Stopping dragging when
     * the MouseOut event occurs is helpful, since the MouseUp event
     * is not reliable, when the mouse is outside the window.
     *
     * @method _stopDragScroll
     */
    _stopDragScroll: function(e) {
        this.dragging = false;
        e.preventDefault();
        e.stopPropagation();
    },

    /**
     * MouseMove event handler that calculates the movement
     * by comparing the mouse positions in the current event and
     * the previous event.
     *
     * @method _dragScroll
     */
    _dragScroll: function(e) {
        if (this.dragging) {
            window.scrollBy(
                this.last_position.clientX - e.clientX,
                this.last_position.clientY - e.clientY);
            this.last_position = e;
            e.preventDefault();
            e.stopPropagation();
        }
    }
};
