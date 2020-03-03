
import daedalus with {
    StyleSheet,
    DomElement,
    TextElement,
}

import 'swipe.js'

const styles = {
    navMenuShadow: StyleSheet({
        position: "fixed",
        left: '0px',
        top: '0px',
    }),
    navMenuShadowHide: StyleSheet({
        width: "1em",
        height: "120vh",
        background: 'rgba(0,0,0,0)',
        border: {width: '1px', style: 'solid'},
        transition: 'background .7s linear, width 0s .7s, height 0s .7s',
    }),
    navMenuShadowShow: StyleSheet({
        width: "100vw",
        height: "120vh",
        background: 'rgba(0,0,0,.6)',
        transition: 'background .7s linear',
    }),
    navMenu: StyleSheet({
        position: "fixed",
        top: '0px',
        width: "300px",
        'min-width': '200px',
        height: "100vh",
        background: 'white',
        border: {right: {style: "solid", "width": "2px", "color": "black"}},
        'box-shadow': '.25em 0 .5em 0 rgba(0,0,0,0.50)',
    }),
    navMenuActionContainer: StyleSheet({
        'overflow': 'auto',
        'height': 'calc(100vh - 120px)',
    }),
    navMenuHide: StyleSheet({
        left: '-300px',
        transition: 'left .5s ease-in-out',
    }),
    navMenuShow: StyleSheet({
        left: '0px',
        transition: 'left .5s ease-in-out',
    }),
    navMenuShowFixed: StyleSheet({
        left: '0px',
    }),
    navMenuHideFixed: StyleSheet({
        left: '-300px',
    }),
    svgDiv: StyleSheet({
        'min-width': '50px',
        'min-height': '50px',
        'width': '50px',
        'height': '50px',
        'margin-right':  '0.5em',
        'margin-left':  '0.5em'
    }),
    actionItem: StyleSheet({
        display: 'flex',
        'border-bottom': {width: '1px', color: '#000000', 'style': 'solid'},
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%',
        height: "60px"
    }),
    header: StyleSheet({
        display: 'flex',
        'border-bottom': {width: '1px', color: '#000000', 'style': 'solid'},
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%',
        height: "120px",
        background: 'green',
    }),

}

StyleSheet(`.${styles.actionItem}:hover`, {
    'background-image': 'linear-gradient(#BCBCBC, #5E5E5E)';
})

StyleSheet(`.${styles.actionItem}:active`, {
    'background-image': 'linear-gradient(#5E5E5E, #BCBCBC)';
})

class NavMenuSvgImpl extends DomElement {
    constructor(url, props) {
        super("img", {src:url, width: 48, height: 48, ...props}, []);
    }
}

class NavMenuSvg extends DomElement {
    constructor(url, props={}) {
        super("div", {className: styles.svgDiv}, [new NavMenuSvgImpl(url, props)])
    }
}

class NavMenuAction extends DomElement {
    constructor(icon_url, text, callback) {
        super("div", {className: styles.actionItem}, []);

        this.attrs = {
            callback,
        }

        this.appendChild(new NavMenuSvg(icon_url))
        this.appendChild(new TextElement(text))
    }

    onClick() {
        this.attrs.callback();
    }
}

class NavMenuHeader extends DomElement {
    constructor() {
        super("div", {className: styles.header}, []);
    }

}

class NavMenuActionContainer extends DomElement {
    constructor() {
        super("div", {className: styles.navMenuActionContainer}, []);
    }
}

class NavMenuImpl extends DomElement {
    constructor() {
        super("div", {className: [styles.navMenu, styles.navMenuHide]}, []);

        this.appendChild(new NavMenuHeader())

        this.attrs = {
            actions: this.appendChild(new NavMenuActionContainer()),
        }


    }

    onClick(event) {
        event.stopPropagation()
        return false;
    }
}

export class NavMenu extends DomElement {
    constructor() {
        super("div", {className: [styles.navMenuShadow, styles.navMenuShadowHide]}, []);

        this.attrs = {
            menu: this.appendChild(new NavMenuImpl(this)),
            fixed: false,
        }

        this.attrs.swipe = new SwipeHandler(document, (pt, direction) => {
            if (direction == SwipeHandler.RIGHT && pt.x < 20) {
                this.show()
            }
        })
    }

    addAction(icon_url, text, callback) {
        this.attrs.menu.attrs.actions.appendChild(
            new NavMenuAction(icon_url, text, callback));
    }

    hide() {
        if (this.attrs.fixed) {
            return
        }
        this.attrs.menu.removeClassName(styles.navMenuHideFixed)

        this.attrs.menu.removeClassName(styles.navMenuShow)
        this.attrs.menu.addClassName(styles.navMenuHide)

        this.removeClassName(styles.navMenuShadowShow)
        this.addClassName(styles.navMenuShadowHide)
    }

    show() {
        if (this.attrs.fixed) {
            return
        }
        this.attrs.menu.removeClassName(styles.navMenuHideFixed)

        this.attrs.menu.removeClassName(styles.navMenuHide)
        this.attrs.menu.addClassName(styles.navMenuShow)

        this.removeClassName(styles.navMenuShadowHide)
        this.addClassName(styles.navMenuShadowShow)
    }

    showFixed(fixed) {

        if (!!fixed) {
            this.attrs.menu.removeClassName(styles.navMenuHide)
            this.attrs.menu.removeClassName(styles.navMenuShow)
            this.attrs.menu.removeClassName(styles.navMenuHideFixed)

            this.attrs.menu.addClassName(styles.navMenuShowFixed)
        } else {

            this.attrs.menu.addClassName(styles.navMenuHideFixed)
            this.attrs.menu.removeClassName(styles.navMenuShowFixed)
        }

        this.attrs.fixed = fixed
    }

    toggle() {
        if (this.hasClassName(styles.navMenuShadowShow)) {
            this.hide()
        } else {
            this.show()
        }
    }

    onClick() {
        this.toggle()
    }
}


NavMenu.DEFAULT_WIDTH = "300px";
