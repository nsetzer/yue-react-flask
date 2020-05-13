

include "./svg.js"

const style = {
    chkbox: StyleSheet({
        'cursor': 'pointer',
    })
}
export class CheckBoxElement extends SvgElement {
    constructor(callback, initialCheckState) {

        super(null, {width: 20, height: 32, className: style.chkbox})

        if (initialCheckState === undefined) {
            throw "error null state: " + initialCheckState
        }
        this.props.src = this.getStateIcons()[initialCheckState]


        this.attrs = {
            callback,
            checkState: initialCheckState,
            initialCheckState,
        }

    }

    setCheckState(checkState) {
        this.attrs.checkState = checkState
        this.props.src = this.getStateIcons()[checkState];
        this.update();
    }

    onClick(event) {
        this.attrs.callback()
    }

    getStateIcons() {
        return [
            resources.svg.checkbox_unchecked,
            resources.svg.checkbox_checked,
            resources.svg.checkbox_partial,
        ];
    }
}

CheckBoxElement.UNCHECKED = 0;
CheckBoxElement.CHECKED = 1;
CheckBoxElement.PARTIAL = 2;
