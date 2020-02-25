
import daedalus with {
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

        // interesting kerning bug with "The Word"
        // the cutoff point is at index 4 causing the space to be collapsed
        // replace spaces with non breaking spaces to preserve the correct
        // kerning
        // TODO: doesnt seem to work perfectly
        text = text.replace(" ", "\xa0")

        if (text.length > 4) {
            const idx = text.length - 4;
            const text1 = text.substr(0, idx);
            const text2 = text.substr(idx, 4);

            this.updateProps({className: [style.ellideMiddle, style.textSpacer]});

            this.appendChild(new DomElement("div",
                {className: style.ellideMiddleDiv1},
                [new TextElement(text1)]));

            this.appendChild(new DomElement("div",
                {className: style.ellideMiddleDiv2},
                [new TextElement(text2)]));
        } else {
            this.appendChild(new TextElement(text))
        }

    }

    setText(text) {
        const idx = text.length - 4;
        const text1 = text.substr(0, idx);
        const text2 = text.substr(idx, 4);
        this.children[0].children[0].setText(text1)
        this.children[1].children[0].setText(text2)
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