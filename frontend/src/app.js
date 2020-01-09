

import daedalus with {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextInputElement,
    Router
}
import api
import pages

const styles = {
    // style the body of the page red so that if we ever see
    // red then something is wrong.
    // set margin/padding to zero to never show the body
    body: StyleSheet({
        margin:0,
        padding:0,
        //background: {color: 'red'}
    }),
    root: StyleSheet({
        width: '100vw',
        height: '100vh',
        margin: {left: 0, top: 0, bottom: 0, right: 0},
        padding: 0,
        //background: {color: 'cyan'}
    }),
}

function isAuthenticated() {
    return new Promise(function(resolve, reject) {
        resolve(api.getUsertoken() !== null)
    })
}

function isNotAuthenticated() {
    return new Promise(function(resolve, reject) {
        resolve(api.getUsertoken() === null)
    })
}

function reqAuth(elem) {
    element = new daedalus.AuthenticateElement(
        elem,
        isAuthenticated,
        () => {},
        () => {history.pushState({}, "", "/")}
    )
    //element.updateProps({style: {height: '100%', width: '100%', 'background-color': '#00FF0033'}})
    return element;
}

function reqNoAuth(elem) {
    element = new daedalus.AuthenticateElement(
        elem,
        isNotAuthenticated,
        () => {},
        () => {history.pushState({}, "", "/u/storage/list")}
    )
    //element.updateProps({style: {height: '100%', width: '100%', 'background-color': '#FFFF0033'}})
    return element;
}

export class Root extends DomElement {

    constructor() {
        super("div", {className: styles.root}, []);

        const body = document.getElementsByTagName("BODY")[0];
        body.className = styles.body

        this.attrs = {
            main: () => new pages.LandingPage(),
            login: () => reqNoAuth(new pages.LoginPage()),
            user_storage: () => reqAuth(new pages.StoragePage()),
            user_storage_preview: () => reqAuth(new pages.StoragePreviewPage()),
            user: () => reqAuth(new DomElement('div', {}, [])),
            'public': () => new DomElement('div', {}, [])
        }

    }

    buildRouter() {
        this.attrs.router = new Router([
            {pattern: "/u/storage/preview/:path*",   element: this.attrs.user_storage_preview},
            {pattern: "/u/storage/:mode/:path*",   element: this.attrs.user_storage},
            {pattern: "/u/:path*",   element: this.attrs.user},
            {pattern: "/p/:path*",   element: this.attrs.public},
            {pattern: "/login",      element: this.attrs.login},
            {pattern: "/:path*",     element: this.attrs.main},
        ], ()=>{return new Home()})

        // TODO: RHS margin is browser and OS Dependant
        this.attrs.router.updateProps({style: {'margin-right': '17px'}})

        //this.attrs.router.updateProps({style: {height: '100%', width: '100%', 'background-color': '#FFFFFF33'}})
        this.appendChild(this.attrs.router)
    }

    elementMounted() {
        // TODO: don't create the Router until after the token
        // is validated
        const token = api.getUsertoken()
        if (token) {
            api.validate_token(token)
                .then((data) => {
                    if (!data.token_is_valid) {
                        api.clearUserToken()

                    }
                    this.buildRouter()
                })
                .catch((err) => {console.error(err)})
        } else {
            this.buildRouter()
        }
    }
}


