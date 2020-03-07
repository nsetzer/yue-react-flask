
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
        //'margin-right': '1em'
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
    treeItem0: StyleSheet({}),
    treeItemN: StyleSheet({'padding-left': '32px'}),
    listItemMid: StyleSheet({
        'margin-left': '1em',
        'flex-grow': '1',
    }),
    listItemEnd: StyleSheet({
        'margin-left': '1em',
        'margin-right': '1em',
        'cursor': 'pointer'
    }),

    listItemSelected: StyleSheet({
        background: '#00FF0022',
        'font-weight': 'bold'
    }),

    treeFooter: StyleSheet({
        height: '33vh',
        'min-height': '64px'
    })

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

        //this.appendChild(new DomElement("div", {className: style.treeItemButtonH}, []))
        //this.appendChild(new DomElement("div", {className: style.treeItemButtonV}, []))

        this.attrs = {callback}
    }

    onClick() {
        this.attrs.callback()
    }
}

const UNSELECTED = 0
const SELECTED = 1
const PARTIAL = 2

export class TreeItem extends DomElement {

    constructor(depth, title, obj) {
        super("div", {className: [style.treeItem]}, []);

        this.attrs = {
            depth,
            title,
            obj,
            children: null,
            selected: false
        }


        this.attrs.container1 = this.appendChild(new DomElement("div", {className: [style.treeItemObjectContainer]}, []))
        this.attrs.container2 = this.appendChild(new DomElement("div", {className: [style.treeItemChildContainer]}, []))

        if (this.hasChildren()) {
            this.attrs.btn = this.attrs.container1.appendChild(
                new TreeButton(this.handleToggleExpand.bind(this)))
        }

        this.attrs.txt = this.attrs.container1.appendChild(new components.MiddleText(title))
        this.attrs.txt.addClassName(style.listItemMid)
        this.attrs.txt.props.onClick = this.handleToggleSelection.bind(this)


        if (depth === 0) {
            this.addClassName(style.treeItem0)
        } else {
            this.addClassName(style.treeItemN)
        }

    }

    setMoreCallback(callback) {
        this.attrs.more = this.attrs.container1.appendChild(
            new SvgMoreElement(callback))
    }

    handleToggleExpand() {

        if (!this.hasChildren()) {
            return
        }

        if (this.attrs.children === null) {
            this.attrs.children = this.buildChildren(this.attrs.obj)
            if (this.attrs.selected) {
                this.attrs.children.forEach(child => {
                    child.setSelected(true)
                })
            }

        }

        if (this.attrs.container2.children.length === 0) {
            this.attrs.container2.children = this.attrs.children
            this.attrs.container2.update()
        } else {
            this.attrs.container2.children = []
            this.attrs.container2.update()
        }
    }

    handleToggleSelection() {
        this.setSelected(!this.attrs.selected)

    }

    setSelected(selected) {
        this.attrs.selected = selected

        if (!!this.attrs.children) {
            this.attrs.children.forEach(child => {
                child.setSelected(selected)
            })
        }

        if (this.attrs.selected) {
            this.attrs.container1.addClassName(style.listItemSelected)
        } else {
            this.attrs.container1.removeClassName(style.listItemSelected)
        }
    }

    countSelected() {

        let sum = 0

        if (this.attrs.children !== null) {
            sum += this.attrs.children.reduce((total, child) => {
                total += child.attrs.selected?1:0
                total += child.countSelected()
                return total
            }, 0)
        }

        sum += this.attrs.selected?1:0

        return sum
    }

    isSelected() {
        return this.attrs.selected
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
    constructor() {
        super("div", {className: style.treeView}, []);

        this.attrs = {
            container: new DomElement("div", {}, []),
            footer: new DomElement("div", {className: style.treeFooter}, []),
        }

        this.appendChild(this.attrs.container)
        this.appendChild(this.attrs.footer)
    }

    reset() {
        this.attrs.container.removeChildren()
    }

    addItem(item) {
        this.attrs.container.appendChild(item)
    }


    countSelected() {
        return this.attrs.container.children.reduce((total, child) => {
            return total + child.countSelected()
        }, 0)
    }

    selectAll(selected) {

        this.attrs.container.children.forEach(child => {
            child.setSelected(selected)
        })

    }
}