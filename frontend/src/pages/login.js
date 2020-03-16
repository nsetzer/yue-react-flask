
from module daedalus import {
    StyleSheet,
    DomElement,
    ButtonElement,
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
        'margin-left': 'auto',
        'margin-right': 'auto',
        'margin-bottom': '1em',
        width: '50%',
    }),
    edit: StyleSheet({
        width: '75%',
        'margin-left': 'auto',
        'margin-right': 'auto',
        'margin-bottom': '1em',
    }),
}

export class LoginPage extends DomElement {
    constructor() {
        super("div", {className: styles.main}, []);

        this.attrs = {
            btn1: new ButtonElement("Login", this.handleLoginClicked.bind(this)),
            btn2: new ButtonElement("Cancel", ()=>{
                history.pushState({}, "", "/")
            }),
            edit_username: new TextInputElement(""),
            edit_password: new TextInputElement(""),
        }

        this.attrs.btn1.addClassName(styles.btn_center)
        this.attrs.btn2.addClassName(styles.btn_center)

        this.attrs.edit_username.addClassName(styles.edit)
        this.attrs.edit_password.addClassName(styles.edit)

        this.attrs.edit_username.updateProps({placeholder: 'Username'})
        this.attrs.edit_password.updateProps({placeholder: 'Password', type: 'password'})

        this.appendChild(this.attrs.edit_username)
        this.appendChild(this.attrs.edit_password)
        this.appendChild(this.attrs.btn1)
        this.appendChild(this.attrs.btn2)
    }

    handleLoginClicked() {
        const username = this.attrs.edit_username.props.value
        const password = this.attrs.edit_password.props.value

        api.authenticate(username, password)
            .then((data) => {
                if (data.token) {
                    api.setUsertoken(data.token)
                    history.pushState({}, "", "/u/storage/list")
                } else {
                    console.error(data.error)
                }
            })
            .catch((err) => {console.error(err)})
    }
}

//export class LoginPage extends DomElement {
//    constructor() {
//        super("div", {className: styles.main}, [new Panel()]);
//    }
//
//}