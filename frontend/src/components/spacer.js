

import module daedalus

export class HSpacer extends DomElement {

    constructor(width) {
        super("div", {}, [])
        this.attrs = {width}
    }

    elementMounted() {
        this._setWidth();
    }

    setWidth(width) {
        this.attrs.width = width
        this._setWidth();
    }

    _setWidth() {
        const node = this.getDomNode();

        if (!!node) {
            node.style['max-width'] = this.attrs.width
            node.style['min-width'] = this.attrs.width
            node.style['width'] = this.attrs.width
            node.style['max-height'] = "1px"
            node.style['min-height'] = "1px"
            node.style['height'] = "1px"
        }
    }
}

export class VSpacer extends DomElement {

    constructor(height) {
        super("div", {}, [])
        this.attrs = {height}
    }

    elementMounted() {
        this._setHeight();
    }

    setWidth(width) {
        this.attrs.height = height
        this._setHeight();
    }

    _setWidth() {
        const node = this.getDomNode();

        if (!!node) {
            node.style['max-height'] = this.attrs.height
            node.style['min-height'] = this.attrs.height
            node.style['height'] = this.attrs.height
            node.style['max-width'] = "1px"
            node.style['min-width'] = "1px"
            node.style['width'] = "1px"
        }
    }
}