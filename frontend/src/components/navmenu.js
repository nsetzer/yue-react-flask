
from module daedalus import {
    StyleSheet,
    DomElement,
    TextElement,
}

include './swipe.js'
include './spacer.js'

const style = {
    navMenuShadow: StyleSheet({
        position: "fixed",
        left: '0px',
        top: '0px',
    }),
    navMenuShadowHide: StyleSheet({
        width: "1em",
        height: "100vh",
        background: 'rgba(0,0,0,0)',
        'border-right': {width: '1px', style: 'solid', color: '#00000033'},
        transition: 'background .7s linear, width 0s .7s, height 0s .7s',
    }),
    alignRight: StyleSheet({
        position: "fixed",
        right: '0px',
        top: '0px',
        width: "1em",
        height: "100vh",
        background: 'rgba(0,0,0,0)',
        'border-left': {width: '1px', style: 'solid', color: '#00000033'},
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
        'margin-left':  '0.5em',
        display: "flex",
        justify-content: "center",
        align-items: "center",
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
    subActionItem: StyleSheet({
        height: "45px"
    }),
    header: StyleSheet({
        display: 'flex',
        'border-bottom': {width: '1px', color: '#000000', 'style': 'solid'},
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%',
        height: "120px",
        background: 'linear-gradient(#08B214, #078C12)',
    }),

}

StyleSheet(`.${style.actionItem}:hover`, {
    'background-image': 'linear-gradient(#BCBCBC, #5E5E5E)';
})

StyleSheet(`.${style.actionItem}:active`, {
    'background-image': 'linear-gradient(#5E5E5E, #BCBCBC)';
})

class NavMenuSvgImpl extends DomElement {
    constructor(url, size, props) {
        super("img", {src:url, width: size, height: size, ...props}, []);
    }
}

class NavMenuSvg extends DomElement {
    constructor(url, size=48, props={}) {
        super("div", {className: style.svgDiv}, [new NavMenuSvgImpl(url, size, props)])
    }
}

class NavMenuAction extends DomElement {
    constructor(icon_url, text, callback) {
        super("div", {className: style.actionItem}, []);

        this.attrs = {
            callback,
        }

        this.appendChild(new NavMenuSvg(icon_url, 48))
        this.appendChild(new TextElement(text))
    }

    onClick() {
        this.attrs.callback();
    }
}

class NavMenuSubAction extends DomElement {
    constructor(icon_url, text, callback) {
        super("div", {className: [style.actionItem, style.subActionItem]}, []);

        this.attrs = {
            callback,
        }

        this.appendChild(new HSpacer("2em"))
        this.appendChild(new NavMenuSvg(icon_url, 32))
        this.appendChild(new TextElement(text))
    }

    onClick() {
        this.attrs.callback();
    }
}

class NavMenuHeader extends DomElement {
    constructor() {
        super("div", {className: style.header}, []);
    }

}

class NavMenuActionContainer extends DomElement {
    constructor() {
        super("div", {className: style.navMenuActionContainer}, []);
    }
}

class NavMenuImpl extends DomElement {
    constructor() {
        super("div", {className: [style.navMenu, style.navMenuHide]}, []);

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
        super("div", {className: [style.navMenuShadow, style.navMenuShadowHide]}, []);

        this.attrs = {
            menu: this.appendChild(new NavMenuImpl(this)),
            fixed: false,
        }


        this.appendChild(new DomElement("div", {
            className: style.alignRight,
            onClick: (event) => event.stopPropagation()
        }, []))

        this.attrs.swipe = new SwipeHandler(document, (pt, direction) => {
            // if the transition is enabled then
            // this.attrs.menu.getDomNode().style.left = pt.xc - 300
            // can be used to set the menu position to the drag position
            if (direction == SwipeHandler.RIGHT && pt.x < 20) {
                this.show()
            }
        })
    }

    addAction(icon_url, text, callback) {
        this.attrs.menu.attrs.actions.appendChild(
            new NavMenuAction(icon_url, text, callback));
    }

    addSubAction(icon_url, text, callback) {
        this.attrs.menu.attrs.actions.appendChild(
            new NavMenuSubAction(icon_url, text, callback));
    }

    hide() {
        if (this.attrs.fixed) {
            return
        }
        this.attrs.menu.removeClassName(style.navMenuHideFixed)

        this.attrs.menu.removeClassName(style.navMenuShow)
        this.attrs.menu.addClassName(style.navMenuHide)

        this.removeClassName(style.navMenuShadowShow)
        this.addClassName(style.navMenuShadowHide)
    }

    show() {
        if (this.attrs.fixed) {
            return
        }
        this.attrs.menu.removeClassName(style.navMenuHideFixed)

        this.attrs.menu.removeClassName(style.navMenuHide)
        this.attrs.menu.addClassName(style.navMenuShow)

        this.removeClassName(style.navMenuShadowHide)
        this.addClassName(style.navMenuShadowShow)
    }

    showFixed(fixed) {

        if (!!fixed) {
            // display permanently on left side
            this.attrs.menu.removeClassName(style.navMenuHide)
            this.attrs.menu.removeClassName(style.navMenuShow)
            this.attrs.menu.removeClassName(style.navMenuHideFixed)

            this.attrs.menu.addClassName(style.navMenuShowFixed)

            this.addClassName(style.navMenuShadowHide)
            this.removeClassName(style.navMenuShadowShow)

        } else {
            // remove
            this.attrs.menu.addClassName(style.navMenuHideFixed)
            this.attrs.menu.removeClassName(style.navMenuShowFixed)

            this.addClassName(style.navMenuShadowHide)
            this.removeClassName(style.navMenuShadowShow)
        }

        this.attrs.fixed = fixed
    }

    toggle() {
        if (this.hasClassName(style.navMenuShadowShow)) {
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
