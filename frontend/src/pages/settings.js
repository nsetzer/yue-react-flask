from module daedalus import{
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    TextInputElement,
    Router
}
import module api
import module components

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

    settingsItem: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'padding-left': '1.1em',
        'padding-bottom': '.5em',
        //width: '100%',
        border: {style: "solid", width: "1px"}
    }),
}

class SettingsItem extends DomElement {
    constructor(title) {
        super("div", {className: style.settingsItem}, []);


        this.appendChild(new TextElement(title))
    }
}

class SettingsGroupItem extends DomElement {
    constructor(title, names) {
        super("div", {}, []);

        this.appendChild(new TextElement(title))

        this.appendChild(new DomElement("br", {}, []))

        const form = this.appendChild(new DomElement("form", {}, []))
        names.forEach(name => {

            const child = form.appendChild(new DomElement("div", {}, []))
            const btn = child.appendChild(new DomElement("input", {type:"radio", value: name, name: this.props.id}));
            child.appendChild(new DomElement("label", {'forx': btn.props.id}, [new TextElement(name)]))
            //child.appendChild(new DomElement("br", {}, []))
        }
    }
}

class Header extends DomElement {
    constructor(parent) {
        super("div", {className: style.header}, []);

        this.appendChild(new components.MiddleText("Settings"))
    }
}

export class SettingsPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            header: new Header(this),
            container: new DomElement("div", {}, [])
        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.container)


        this.attrs.container.appendChild(new SettingsItem("Volume:"))
        this.attrs.container.appendChild(new SettingsGroupItem("Audio Backend:", ["Cloud", "Cloud Native", "Native"]))

    }

}