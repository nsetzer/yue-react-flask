
from module daedalus import {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextInputElement,
    Router
}
import module api

const style = {
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
        'box-shadow': '5px 5px 5px 5px rgba(0,0,0,.6)'
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
    warning: StyleSheet({
        'margin-bottom': '1em',
        background: '#AA2211',
        box-shadow:  '0 0 8px 8px #AA2211',
        'margin-left': 'auto',
        'margin-right': 'auto',
        width: '66%',
    }),
    hide: StyleSheet({display: 'none'})
}

export class LoginPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            btn1: new ButtonElement("Login", this.handleLoginClicked.bind(this)),
            btn2: new ButtonElement("Cancel", ()=>{
                history.pushState({}, "", "/")
            }),
            edit_username: new TextInputElement(""),
            edit_password: new TextInputElement(""),
            warning: new DomElement("div", {className: style.warning}, [new TextElement("Invalid Username or Password")])
        }

        this.attrs.btn1.addClassName(style.btn_center)
        this.attrs.btn2.addClassName(style.btn_center)

        this.attrs.edit_username.addClassName(style.edit)
        this.attrs.edit_password.addClassName(style.edit)

        this.attrs.edit_username.updateProps({placeholder: 'Username'})
        this.attrs.edit_password.updateProps({placeholder: 'Password', type: 'password'})

        this.attrs.warning.addClassName(style.hide)

        this.appendChild(this.attrs.edit_username)
        this.appendChild(this.attrs.edit_password)
        this.appendChild(this.attrs.warning)
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
                    this.attrs.warning.addClassName(style.hide)
                    history.pushState({}, "", "/u/storage/list")
                } else {
                    this.attrs.warning.removeClassName(style.hide)
                    console.error(data.error)
                }
            })
            .catch((err) => {
                this.attrs.warning.removeClassName(style.hide)
                console.error(err)
            })
    }
}

//export class LoginPage extends DomElement {
//    constructor() {
//        super("div", {className: styles.main}, [new Panel()]);
//    }
//
//}