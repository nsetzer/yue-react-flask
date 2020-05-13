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
        //'background': '#078C12',
        'background': '#0cb51a',
        //          linear-gradient(90deg, rgba(62, 68, 74, 0.50), rgba(192, 192, 192, 0.4), rgba(91, 96, 105, 0.5)),
        //repeating-linear-gradient( 0deg, rgba( 1,  5,  8, 0.26), rgba(189, 189, 189, 0.4) 2.5px),
        //repeating-linear-gradient( 0deg, rgba( 2, 23, 38, 0.32), rgba(192, 192, 192, 0.4) 2.7px),
        //repeating-linear-gradient( 0deg, rgba(58, 65, 71, 0.60), rgba(224, 226, 227, 0.3) 3.0px),
        //repeating-linear-gradient( 0deg, rgba(91, 95, 98, 0.50), rgba( 55, 170, 233, 0.26) 4.5px)
        //background-image: "linear-gradient(90deg, rgba(11, 43, 75, 0.6), rgba(23, 119, 180, 0.42), rgba(39, 64, 108, 0.6)), repeating-linear-gradient(0deg, rgba(1, 5, 8, 0.26), rgba(77, 142, 191, 0.41) 2.5px), repeating-linear-gradient(0deg, rgba(2, 23, 38, 0.32), rgba( 54, 149, 194, 0.4) 2.7px), repeating-linear-gradient(0deg, rgba( 2, 42, 71, 0.64), rgba( 58, 176, 231, 0.3) 3.0px), repeating-linear-gradient(0deg, rgba(16, 67, 104, 1.0), rgba(55, 170, 233, 0.26) 4.5px)",
        //background-image: "linear-gradient(90deg, rgba(62, 68, 74, 0.5), rgba(192, 192, 192, 0.4), rgba(91, 96, 105, 0.5)), repeating-linear-gradient(0deg, rgba(1, 5, 8, 0.26), rgba(189, 189, 189, 0.4) 2.5px), repeating-linear-gradient(0deg, rgba(2, 23, 38, 0.32), rgba(192, 192, 192, 0.4) 2.7px), repeating-linear-gradient(0deg, rgba(58, 65, 71, 0.60), rgba(224, 226, 227, 0.3) 3.0px), repeating-linear-gradient(0deg, rgba(91, 95,  98, 0.5), rgba(55, 170, 233, 0.26) 4.5px)",
        top:0,
        left:0,
        right:0,
        //'z-index': '1'
        min-height:"16px",
        'box-shadow': '0 .25em .5em 0 rgba(0,0,0,0.50)',
    }),
    footer: StyleSheet({
        'text-align': 'center',
        'position': 'fixed',
        'background': '#0cb51a',
        bottom:0,
        left:0,
        right:0,
        min-height:"32px",
        //width: '100%',
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

    toolbarFooter: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'justify-content': 'flex-end',
        'align-items': 'center',
        width: '100%',
        'background-image': 'linear-gradient(#08B214, #078C12)',
        'border-bottom': "solid 1px black"
    }),

    toolbarFooterInner: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'padding-left': '1em',
        'padding-right': '1em',
        //flex-flow: 'row-reverse',
        justify-content: 'flex-end',
    }),

    toolbar2: StyleSheet({
        display: 'block',
        'flex-direction': 'row',
        //'justify-content': 'flex-start',
        //'align-items': 'center',
        width: '100%',
    }),

    toolbarInner2: StyleSheet({
        display: 'flex',
        //'flex-grow': 1,
        'align-items': 'center',
        'justify-content': 'center',
        'padding-left': '1em',
        'padding-right': '1em',
        width: "calc(100%-2em)",
    }),


    toolbar2Start: StyleSheet({
        'justify-content': 'flex-start',
        'align-items': 'center',
    }),

    toolbar2Center: StyleSheet({
        'justify-content': 'center',
        'align-items': 'center',
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


export class NavFooter extends DomElement {
    constructor() {
        super("div", {className: style.footer}, []);

        this.attrs = {
            div: new DomElement("div", {className: style.headerDiv}, []),
            toolbar: new DomElement("div", {className: style.toolbarFooter}, []),
            toolbarInner: new DomElement("div", {className: style.toolbarFooterInner}, []),
        }

        this.appendChild(this.attrs.div)
        this.attrs.div.appendChild(this.attrs.toolbar)
        this.attrs.toolbar.appendChild(this.attrs.toolbarInner)

    }

    addAction(icon, callback) {
        this.attrs.toolbarInner.appendChild(
            new SvgButtonElement(icon, callback))
    }

}