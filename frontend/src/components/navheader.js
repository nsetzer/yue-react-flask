from module daedalus import {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    TextInputElement,
    Router
}

include './svg.js'

const style = {

    header: StyleSheet({
        'text-align': 'center',
        'position': 'sticky',
        'background': '#078C12',
        top:0,
        //'z-index': '1'
    }),
    headerDiv: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'justify-content': 'flex-start',
        'align-items': 'center',
        //width: '100%',

    }),

    toolbar: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%',
        'background-image': 'linear-gradient(#08B214, #078C12)',
        'border-bottom': "solid 1px black"
    }),

    toolbarInner: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'padding-left': '1em',
        'padding-right': '1em',
    }),

    toolbar2: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        //'justify-content': 'flex-start',
        //'align-items': 'center',
        width: '100%',
    }),

    toolbar2Start: StyleSheet({
        'justify-content': 'flex-start',
        'align-items': 'center',
    }),

    toolbar2Center: StyleSheet({
        'justify-content': 'center',
        'align-items': 'center',
    }),

    toolbarInner2: StyleSheet({
        display: 'flex',
        'flex-grow': 1,
        'align-items': 'center',
        'justify-content': 'center',
        'padding-left': '1em',
        'padding-right': '1em',
    }),

    grow: StyleSheet({
        'flex-grow': 1,
    }),
    pad: StyleSheet({
        'width': '1em',
    }),
}

export class NavHeader extends DomElement {
    constructor() {
        super("div", {className: style.header}, []);

        this.attrs = {
            div: new DomElement("div", {className: style.headerDiv}, []),
            toolbar: new DomElement("div", {className: style.toolbar}, []),
            toolbarInner: new DomElement("div", {className: style.toolbarInner}, []),
            rows: [],
        }

        this.appendChild(this.attrs.div)
        this.attrs.div.appendChild(this.attrs.toolbar)
        this.attrs.toolbar.appendChild(this.attrs.toolbarInner)

    }

    addAction(icon, callback) {
        this.attrs.toolbarInner.appendChild(
            new SvgButtonElement(icon, callback))
    }

    addRow(center=false) {
        let outer = new DomElement("div", {className: style.toolbar2}, []);

        if (center) {
            outer.addClassName(style.toolbar2Center)
        } else {
            outer.addClassName(style.toolbar2Start)
        }
        let inner = new DomElement("div", {className: style.toolbarInner2}, []);

        outer.appendChild(inner);
        outer.attrs.inner = inner;

        this.attrs.div.appendChild(outer);
        this.attrs.rows.push(outer);

        return inner;

    }

    addRowElement(rowIndex, element) {
        this.attrs.rows[rowIndex].children[0].appendChild(element)
    }

    addRowAction(rowIndex, icon, callback) {
        this.attrs.rows[rowIndex].children[0].appendChild(
            new SvgButtonElement(icon, callback))
    }
}