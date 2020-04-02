
from module daedalus import {
    DomElement,
}

const style = {
    svgButton: StyleSheet({
        //'background-image': 'linear-gradient(#D5D5D5, #6A6A6A)',
        //'margin-right': '.5em',
        //'margin-bottom': '.5em',
        padding: '4px',
        padding-right:'.5em'
    }),
    svgButton2: StyleSheet({
        //'background-image': 'linear-gradient(#D5D5D5, #6A6A6A)',
        //'margin-left': '.5em',
        //'margin-bottom': '.5em',
        padding: '4px',
        padding-left:'.5em'
    }),
}

StyleSheet(`.${style.svgButton}:active`, {
    background: '#00000030',
})

StyleSheet(`.${style.svgButton2}:active`, {
    background: '#00000030',
})

export class SvgElement extends DomElement {
    constructor(url, props) {
        super("img", {src:url, ...props}, [])
    }

    onLoad(event) {
        // the backup image doesn't effect the work queue
        console.warn("success loading: ", this.props.src)
    }

    onError(error) {
        console.warn("error loading: ", this.props.src, JSON.stringify(error))
    }
}

export class SvgButtonElement extends SvgElement {
    constructor(url, callback) {
        super(url, {width: 32, height: 32, className: style.svgButton});
        this.attrs = {callback};
    }

    onClick(event) {
        if (this.attrs.callback) {
            this.attrs.callback()
        }
    }
}

export class SvgButtonElement2 extends SvgElement {
    constructor(url, callback) {
        super(url, {width: 32, height: 32, className: style.svgButton2});
        this.attrs = {callback};
    }

    onClick(event) {
        if (this.attrs.callback) {
            this.attrs.callback()
        }
    }
}