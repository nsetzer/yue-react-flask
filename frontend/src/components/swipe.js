
export class SwipeHandler {

    constructor(parent, callback) {
        this.mount(parent)
        this.callback = callback

        this.xDown = null;
        this.yDown = null;
    }

    mount(dom) {
        // i.e. dom = document
        console.log("mount", dom)
        dom.addEventListener('touchstart', this.handleTouchStart.bind(this), false);
        dom.addEventListener('touchmove', this.handleTouchMove.bind(this), false);
    }

    getTouches(evt) {
        return evt.touches || evt.originalEvent.touches;
    }

    handleTouchStart(evt) {
        //this.callback(0, -1)

        try {
            const firstTouch = this.getTouches(evt)[0];
            this.xDown = firstTouch.clientX;
            this.yDown = firstTouch.clientY;

            let pt = {x: this.xDown, y: this.yDown}
            this.callback(pt, 0)
        } catch (e) {
            this.callback({x:0, y:0}, e)
        }
    };

    handleTouchMove(evt) {
        if ( ! this.xDown || ! this.yDown ) {
            return;
        }


        let xUp = evt.touches[0].clientX;
        let yUp = evt.touches[0].clientY;

        let xDiff = this.xDown - xUp;
        let yDiff = this.yDown - yUp;


        let pt = {x: this.xDown, y: this.yDown, dx: xDiff, dy: yDiff}

        let direction = 0

        if ( Math.abs( xDiff ) > Math.abs( yDiff ) ) {
            if ( xDiff > 0 ) {
                direction = SwipeHandler.LEFT
            } else {
                direction = SwipeHandler.RIGHT
            }
        } else {
            if ( yDiff > 0 ) {
                direction = SwipeHandler.UP
            } else {
                direction = SwipeHandler.DOWN
            }
        }

        if (direction != 0) {
            this.callback(pt, direction)
        }

        /* reset values */
        this.xDown = null;
        this.yDown = null;
    };
}

SwipeHandler.UP = 1
SwipeHandler.DOWN = 2
SwipeHandler.RIGHT = 3
SwipeHandler.LEFT = 4
