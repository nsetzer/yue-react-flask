
from module daedalus import {
    StyleSheet,
    DomElement,
    TextElement,
}

const style = {
    // http://jsfiddle.net/4ah8ernc/2/

    ellideMiddle: StyleSheet({
        display: 'inline-flex',
        'flex-wrap': 'nowrap',
        'max-width': '100%',
        'min-width': '0',
        // this pushes the text to the bottom
        // which helps when div1 and div2 content
        // content with different line heights
        // options are:
        //  flex-start, flex-end, stretch, center, baseline
        'align-items': 'baseline';
    }),
    ellideMiddleDiv1: StyleSheet({
        flex: '0 1 auto',
        'text-overflow': 'ellipsis',
        overflow: 'hidden',
        'white-space': 'nowrap',
    }),
    ellideMiddleDiv2: StyleSheet({
        flex: '1 0 auto',
        'white-space': 'nowrap',

    }),
    ellideMiddleLink: StyleSheet({
        cursor: 'pointer', color: 'blue'
    }),

}

export class MiddleText extends DomElement {

    // may need to replace spaces with
    constructor(text) {
        super("div", {className: [style.textSpacer]}, [])
        this.pivot = 4;

        // interesting kerning bug with "The Word"
        // the cutoff point is at index 4 causing the space to be collapsed
        // replace spaces with non breaking spaces to preserve the correct
        // kerning
        // TODO: doesnt seem to work perfectly

        this.updateProps({className: [style.ellideMiddle, style.textSpacer]});

        this.appendChild(new DomElement("div",
            {className: style.ellideMiddleDiv1},
            [new TextElement('')]));

        this.appendChild(new DomElement("div",
            {className: style.ellideMiddleDiv2},
            [new TextElement('')]));

        this.setText(text)

    }

    setText(text) {
        if (text.length < this.pivot) {
            this.children[0].children[0].setText(text)
            this.children[1].children[0].setText("")
        } else {
            //text = text.replace(" ", "\xa0")
            //text = text.replace(/ /g, "_")
            text = text.replace(/ /g, "\xa0")
            const idx = text.length - this.pivot;
            const text1 = text.substr(0, idx);
            const text2 = text.substr(idx, this.pivot);
            this.children[0].children[0].setText(text1)
            this.children[1].children[0].setText(text2)
        }

    }
}

export class MiddleTextLink extends MiddleText {
    constructor(text, url) {
        super(text)

        this.state = {
            url
        }

        this.props.className.push(style.ellideMiddleLink)
    }

    onClick() {
        if (this.state.url.startsWith('http')) {
            window.open(this.state.url, '_blank');
        } else {
            history.pushState({}, "", this.state.url)
        }
    }
}