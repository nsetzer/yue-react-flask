
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

        this.attrs.btn1.updateProps({className: styles.btn_center})
        this.attrs.btn2.updateProps({className: styles.btn_center})

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