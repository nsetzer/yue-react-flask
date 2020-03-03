import daedalus with {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    TextInputElement,
    Router
}

import components

const style = {
    main: StyleSheet({
        width: '100%',
    }),

    header: StyleSheet({
        'text-align': 'center',
        'position': 'sticky',
        'background': '#238e23',
        'padding-left': '2em',
        'padding-right': '2em',
        top:0
    }),

}

class Header extends DomElement {
    constructor(parent) {
        super("div", {className: style.header}, []);

        this.appendChild(new components.MiddleText("No Soap Radio"))
    }
}

export class UserRadioPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            header: new Header(this),
            container: new DomElement("div", {}, [])
        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.container)



    }

    elementMounted() {
        console.log("mount radio view")

        api.radioVideoInfo("VHfi4kGPFvc")
            .then(result => {
                console.log(result)
            })
            .catch(error => {
                console.log(error);
            })

    }

}