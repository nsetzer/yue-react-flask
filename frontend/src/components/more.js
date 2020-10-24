



const style = {

    moreMenuShadow: StyleSheet({
        position: 'fixed',
        top: '0',
        left: '0',
        background: 'rgba(0,0,0,0.33)',
        width: '100vw',
        height: '120vh', // a little extra for mobile browsers
        'z-index': '1000',
    }),
    moreMenu: StyleSheet({
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        background: 'white',
        width: '50vw',
        'min-width': '10em',
        'min-height': '10em',
        'box-shadow': '.5em .5em .5em 0 rgba(0,0,0,0.50)',
        padding: '1em',
        'z-index': '1000',
    }),
    moreMenuShow: StyleSheet({display: 'block'}),
    moreMenuHide: StyleSheet({display: 'none'}),

    // light color is chosen,
    // dark color is 50% of light color
    // hover light color is 10% darker,
    // hover dark color is 50% of hover light color
    // border color is HSV half way between both dark colors
    // active color inverts hover
    moreMenuButton: StyleSheet({
        border: {'radius': '.5em', color: '#646464', style: 'solid', width: '1px'},
        padding: '1em',
        'background-image': 'linear-gradient(#D5D5D5, #6A6A6A)',
        'text-align': 'center'
    }),
}

// order of these rules is important, hover before active
StyleSheet(`.${style.moreMenuButton}:hover`, {
    'background-image': 'linear-gradient(#BCBCBC, #5E5E5E)';
})

StyleSheet(`.${style.moreMenuButton}:active`, {
    'background-image': 'linear-gradient(#5E5E5E, #BCBCBC)';
})

class MoreMenuButton extends DomElement {
    constructor(text, callback) {
        super("div", {className: [style.moreMenuButton], onClick: callback}, [new TextElement(text)])
    }

    setText(text) {
        this.children[0].setText(text)
    }

}

class MoreMenuImpl extends DomElement {
    constructor() {
        super("div", {className: [style.moreMenu]}, [])

    }

    onClick(event) {
        event.stopPropagation();
    }
}

export class MoreMenu extends DomElement {
    constructor(callback_close) {
        super("div", {
            className: [style.moreMenuShadow, style.moreMenuHide]
        }, [])

        this.attrs = {
            callback_close,
            impl: this.appendChild(new MoreMenuImpl())
        }
    }

    onClick() {
        this.attrs.callback_close()
    }

    addAction(text, callback) {
        this.attrs.impl.appendChild(new MoreMenuButton(text, () => {
            callback();
            this.hide();
        }))
    }

    hide() {
        this.updateProps({className: [style.moreMenuShadow, style.moreMenuHide]})

    }

    show() {
        this.updateProps({className: [style.moreMenuShadow, style.moreMenuShow]})
    }

}