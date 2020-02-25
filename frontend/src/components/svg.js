
import daedalus with {
    DomElement,
}

const style = {
    svgButton: StyleSheet({
        'background-image': 'linear-gradient(#D5D5D5, #6A6A6A)',
        'margin-right': '.5em',
        'margin-bottom': '.5em',
        padding: '4px'
    }),
}

StyleSheet(`.${style.svgButton}:hover`, {
    'background-image': 'linear-gradient(#BCBCBC, #5E5E5E)';
})

StyleSheet(`.${style.svgButton}:active`, {
    'background-image': 'linear-gradient(#5E5E5E, #BCBCBC)';
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