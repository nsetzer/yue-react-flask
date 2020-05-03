
import module resources

include './svg.js'

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

    listItemCheck: StyleSheet({
        'margin-left': '1em',
        'margin-right': '1em',
        'cursor': 'pointer',
        'border': 'solid 1px black'
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

function getCheckResource(state) {
    if (state == 2) { // partial
        return resources.svg.sort
    } else if (state == 1) { // checked
        return resources.svg.download
    }

    return resources.svg.select

}

class CheckedElement extends SvgElement {
    constructor(callback, initialCheckState) {

        let res = getCheckResource(initialCheckState)
        super(res, {width: 20, height: 32, className: style.listItemCheck})

        this.attrs = {
            callback,
            checkState: initialCheckState,
            initialCheckState,
        }

    }

    setCheckState(checkState) {
        this.attrs.checkState = checkState
        this.props.src = getCheckResource(checkState);
        this.update();
    }


    onClick(event) {

        this.attrs.callback()
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

    constructor(parent, depth, title, obj, selectMode=1, selected=UNSELECTED) {
        super("div", {className: [style.treeItem]}, []);

        this.attrs = {
            parent,
            depth,
            title,
            obj,
            children: null,
            selected: selected,
            selectMode,
            chk: null,
        }

        this.attrs.container1 = this.appendChild(new DomElement("div", {className: [style.treeItemObjectContainer]}, []))
        this.attrs.container2 = this.appendChild(new DomElement("div", {className: [style.treeItemChildContainer]}, []))

        if (this.hasChildren()) {
            this.attrs.btn = this.attrs.container1.appendChild(
                new TreeButton(this.handleToggleExpand.bind(this)))
        }

        this.attrs.txt = this.attrs.container1.appendChild(new components.MiddleText(title))
        this.attrs.txt.addClassName(style.listItemMid)
        if (selectMode != TreeItem.SELECTION_MODE_CHECK) {
            this.attrs.txt.props.onClick = this.handleToggleSelection.bind(this)
        }

        if (selectMode == TreeItem.SELECTION_MODE_CHECK) {
            this.setCheckEnabled(this.handleToggleSelection.bind(this), selected);
        }

        if (depth === 0) {
            this.addClassName(style.treeItem0)
        } else {
            this.addClassName(style.treeItemN)
        }

    }

    setMoreCallback(callback) {
        this.attrs.more = new SvgMoreElement(callback);
        if (this.attrs.selectMode != TreeItem.SELECTION_MODE_CHECK) {
            this.attrs.container1.appendChild(this.attrs.more);
        } else {
            //
            this.attrs.container1.insertChild(-2, this.attrs.more);
        }
    }

    setCheckEnabled(callback, state) {
        this.attrs.chk = this.attrs.container1.appendChild(
            new CheckedElement(callback, state))
    }

    handleToggleExpand() {

        if (!this.hasChildren()) {
            return
        }

        if (this.attrs.children === null) {
            this.attrs.children = this.buildChildren(this.attrs.obj)

                if (this.attrs.selected == SELECTED) {
                    this.attrs.children.forEach(child => {
                        child.setSelected(SELECTED)
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

        let next = (this.attrs.selected != UNSELECTED)?UNSELECTED:SELECTED;
        this.setSelected(next)

        if (this.attrs.depth > 0 && this.attrs.parent != null) {
            this.attrs.parent.handleFixSelection();
        }

    }

    handleFixSelection() {

        let every = this.attrs.children.every(child => child.attrs.selected == SELECTED)
        let some = this.attrs.children.some(child => child.attrs.selected != UNSELECTED)

        let selected;

        if (every) {
            selected = SELECTED
        } else if (some) {
            selected = PARTIAL
        } else {
            selected = UNSELECTED
        }
        this.setSelectedInternal(selected);

        if (this.attrs.depth > 0 && this.attrs.parent != null) {
            this.attrs.parent.handleFixSelection();
        }
    }

    setSelected(selected) {

        if (!!this.attrs.children) {
            this.attrs.children.forEach(child => {
                child.setSelected(selected)
            })
        }

        this.setSelectedInternal(selected)
    }

    setSelectedInternal(selected) {
        this.attrs.selected = selected

        if (this.attrs.selectMode != TreeItem.SELECTION_MODE_CHECK) {
            if (this.attrs.selected) {
                this.attrs.container1.addClassName(style.listItemSelected)
            } else {
                this.attrs.container1.removeClassName(style.listItemSelected)
            }
        }

        if (this.attrs.chk != null) {
            this.attrs.chk.setCheckState(this.attrs.selected)
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

TreeItem.SELECTION_MODE_HIGHLIGHT = 1
TreeItem.SELECTION_MODE_CHECK = 2

TreeItem.SELECTION_UNSELECTED = UNSELECTED
TreeItem.SELECTION_SELECTED = SELECTED
TreeItem.SELECTION_PARTIAL = PARTIAL

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