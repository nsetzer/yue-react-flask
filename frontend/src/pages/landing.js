
import daedalus with {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextInputElement,
    Router
}
import api

const styles = {
    main: StyleSheet({
        display: 'inline-flex',
        'flex-direction': 'column',
        'justify-content': 'center',
        'margin-top': '25vh',
        'margin-left': '25vw',
        width: '50vw',
        'min-width': '9em',
        height: '50vh',
        'min-height': '6em',
        background: {color: 'blue'}
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
    }

}