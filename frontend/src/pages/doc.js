

from module daedalus import {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    TextInputElement,
    Router
}
import module api


const styles = {
    main: StyleSheet({
    }),
}

export class OpenApiDocPage extends DomElement {
    constructor() {
        super("div", {className: styles.main}, []);

        this.doc = this.appendChild(new DomElement("pre"))

    }

    elementMounted() {

        api.userDoc(location.origin)
            .then((result)=>{this.doc.appendChild(new TextElement(result))})
            .catch((err)=>{console.error(err)})
    }

}