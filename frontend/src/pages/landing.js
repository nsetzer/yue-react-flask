
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
        display: 'inline-flex',
        'flex-direction': 'column',
        'justify-content': 'center',
        'margin-top': '25vh',
        'margin-left': '25%',
        width: '50%',
        'min-width': '9em',
        height: '50vh',
        'min-height': '6em',
        'background-image': 'linear-gradient(#08B214, #078C12)',
        'border': "solid 1px transparent",
        'border-radius': '1em',
        'text-align': 'center',
    }),
    btn_center: StyleSheet({
        'text-align': 'center',
        'margin-left': '25%',
        width: '50%'
    })
}


export class LandingPage extends DomElement {
    constructor() {
        super("div", {className: styles.main}, []);

        this.attrs = {
            btn: new ButtonElement("Login", ()=>{
                history.pushState({}, "", "/login")
            })
        }



        this.attrs.btn.updateProps({className: styles.btn_center})

        this.appendChild(this.attrs.btn)
        this.appendChild(new TextElement(daedalus.env.buildDate))

    }

}