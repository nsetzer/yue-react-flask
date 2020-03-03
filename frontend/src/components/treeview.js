
import resources

import './svg.js'

const style = {

    treeView: StyleSheet({

    }),
    treeItem: StyleSheet({
        'padding-top': '.25em'
    }),
    treeItemButton: StyleSheet({
        width: '32px',
        height: '32px',
        'min-width': '32px',
        'min-height': '32px',
        background: 'blue',
        'margin-right': '1em'
    }),
    treeItemButtonH: StyleSheet({
        position: 'relative',
        top: 0,
        left: 0,
        width: '32px',
        height: '11px',
        'margin-top': '11px',
        background: 'green',
    }),
    treeItemButtonV: StyleSheet({
        position: 'relative',
        top: '-22px',
        left: 0,
        width: '11px',
        height: '32px',
        'margin-left': '11px',
        background: 'green',
    }),
    treeItemObjectContainer: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'align-items': 'center'
    }),
    treeItemChildContainer: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
    }),
    treeItem0: StyleSheet({'padding-left': '1em'}),
    treeItemN: StyleSheet({'padding-left': '32px'}),
    listItemMid: StyleSheet({
        'flex-grow': '1',
    }),
    listItemEnd: StyleSheet({
        'margin-left': '1em',
        'margin-right': '1em',
        'cursor': 'pointer'
    }),

}

StyleSheet(`.${style.treeItemObjectContainer}:hover`, {background: '#0000FF22'})

// todo: copied from storage
class SvgMoreElement extends SvgElement {
    constructor(callback) {

        super(resources.svg.more, {width: 20, height: 32, className: style.listItemEnd})

        this.state = {
            callback
        }

    }

    onClick(event) {
        this.state.callback()
    }
}

class TreeButton extends DomElement {
    constructor(callback) {
        super("div", {className: [style.treeItemButton]}, []);

        this.appendChild(new DomElement("div", {className: style.treeItemButtonH}, []))
        this.appendChild(new DomElement("div", {className: style.treeItemButtonV}, []))

        this.attrs = {callback}
    }

    onClick() {
        this.attrs.callback()
    }
}

export class TreeItem extends DomElement {

    constructor(depth, title, obj) {
        super("div", {className: [style.treeItem]}, []);

        this.attrs = {
            depth,
            title,
            obj,
            children: null
        }


        this.attrs.container1 = this.appendChild(new DomElement("div", {className: [style.treeItemObjectContainer]}, []))
        this.attrs.container2 = this.appendChild(new DomElement("div", {className: [style.treeItemChildContainer]}, []))

        this.attrs.btn = this.attrs.container1.appendChild(new TreeButton(this.handleToggleExpand.bind(this)))
        this.attrs.txt = this.attrs.container1.appendChild(new components.MiddleText(title))
        this.attrs.txt.addClassName(style.listItemMid)

        this.attrs.more = this.attrs.container1.appendChild(new SvgMoreElement(()=>{}))

        if (depth === 0) {
            this.addClassName(style.treeItem0)
        } else {
            this.addClassName(style.treeItemN)
        }

    }

    handleToggleExpand() {

        if (!this.hasChildren()) {
            return
        }

        if (this.attrs.children === null) {
            this.attrs.children = this.buildChildren(this.attrs.obj)
        }

        if (this.attrs.container2.children.length === 0) {
            this.attrs.container2.children = this.attrs.children
            this.attrs.container2.update()
        } else {
            this.attrs.container2.children = []
            this.attrs.container2.update()
        }
    }

    hasChildren() {
        return true;
    }

    buildChildren(obj) {
        return []
    }
}


// construct the top level list
// each item in the list only constructs it's children
// when expanded. this allows for quick rendering
// of a large data set by only constructing on demand
export class TreeView extends DomElement {
    constructor(parent) {
        super("div", {className: style.treeView}, []);


    }

    reset() {
        this.removeChildren()
    }

    addItem(item) {
        this.appendChild(item)
    }
}