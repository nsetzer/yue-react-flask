import daedalus with {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    TextInputElement,
    Router
}
import api

const style = {
    main: StyleSheet({
        width: '100%',
    }),
}


export class SettingsPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, [new TextElement("hello settings")]);

    }

}