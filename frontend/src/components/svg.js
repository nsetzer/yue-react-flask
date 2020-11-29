
from module daedalus import {
    DomElement,
}

const style = {
    svgButton: StyleSheet({
        padding: '4px',
    }),

}

StyleSheet(`.${style.svgButton}:active`, {
    background: '#00000030',
})

export class SvgElement extends DomElement {
    constructor(url, props) {
        super("img", {src:url, ...props}, [])
    }

    onLoad(event) {
        console.warn("success loading: ", this.props.src)
    }

    onError(error) {
        console.warn("error loading: ", this.props.src, JSON.stringify(error))
    }

    /*
    setIcon(url) {
        this.updateProps({src: url})
    }
    */
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

    setUrl(url) {
        this.props.src = url;
        this.update()
    }
}

