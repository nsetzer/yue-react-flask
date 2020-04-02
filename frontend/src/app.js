
/**
TODO: investigate dynamically loading pages

    store each page in a separate js file to be loaded on demand
    display a default loading page while the script loads
    once fully loaded replace the loading page with the actual page

    requires daedalus and router integration

    var script = document.createElement('script');
    script.onload = function () {
        router replace...
    };
    script.src = something;
    document.head.appendChild(script); // initiate script load

*/
from module daedalus import {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    TextInputElement,
    Router
}
import module api
import module pages
import module components
import module resources

const style = {
    body: StyleSheet({
        margin:0,
        padding:0,
        'overflow-y': 'scroll',
        //background: {color: '#CCCCCC'},
    }),
    rootWeb: StyleSheet({
        width: 'calc(100vw - 17px)',
        //height: '100vh',
        margin: {left: 0, top: 0, bottom: 0, right: 0},
        padding: 0,
        //background: {color: 'cyan'}
    }),
    rootMobile: StyleSheet({
        width: '100vw',
        //height: '100vh',
        margin: {left: 0, top: 0, bottom: 0, right: 0},
        padding: 0,
        //background: {color: 'cyan'}
    }),
    margin: StyleSheet({'margin-right': '0px'}),
    fullsize: StyleSheet({'margin-left': "300px"})
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
    const element = new daedalus.AuthenticateElement(
        elem,
        isAuthenticated,
        () => {},
        () => {history.pushState({}, "", "/")}
    )
    //element.updateProps({style: {height: '100%', width: '100%', 'background-color': '#00FF0033'}})
    return element;
}

function reqNoAuth(elem) {
    const element = new daedalus.AuthenticateElement(
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
        super("div", {}, []);

        const body = document.getElementsByTagName("BODY")[0];
        body.className = style.body

        this.attrs = {
            main: () => new pages.LandingPage(),
            login: () => reqNoAuth(new pages.LoginPage()),
            user_storage: () => reqAuth(new pages.StoragePage()),
            user_storage_preview: () => reqAuth(new pages.StoragePreviewPage()),
            user_storage_search: () => reqAuth(new pages.StorageSearchPage()),
            user_playlist: () => reqAuth(new pages.PlaylistPage()),
            user_settings: () => reqAuth(new pages.SettingsPage()),
            user_library: () => reqAuth(new pages.LibraryPage()),
            user_radio: () => reqAuth(new pages.UserRadioPage()),
            user: () => reqAuth(new DomElement('div', {}, [])),
            'public': () => new DomElement('div', {}, []),
            nav: null,
        }

        window.onresize = this.handleResize.bind(this)

    }

    buildRouter() {
        this.attrs.router = new Router([
            {pattern: "/u/storage/preview/:path*",   element: this.attrs.user_storage_preview},
            {pattern: "/u/storage/:mode/:path*",   element: this.attrs.user_storage},
            {pattern: "/u/playlist",   element: this.attrs.user_playlist},
            {pattern: "/u/settings",   element: this.attrs.user_settings},
            {pattern: "/u/library",   element: this.attrs.user_library},
            {pattern: "/u/radio",   element: this.attrs.user_radio},
            {pattern: "/u/:path*",   element: this.attrs.user},
            {pattern: "/p/:path*",   element: this.attrs.public},
            {pattern: "/login",      element: this.attrs.login},
            {pattern: "/:path*",     element: this.attrs.main},
        ], ()=>{return new Home()})

        this.attrs.nav = new components.NavMenu();
        this.attrs.nav.addAction(resources.svg.playlist, "Playlist", ()=>{
            history.pushState({}, "", "/u/playlist");
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.music_note, "Library", ()=>{
            history.pushState({}, "", "/u/library");
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.externalmedia, "Radio", ()=>{
            history.pushState({}, "", "/u/radio");
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.download, "Sync", ()=>{
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.documents, "Storage", ()=>{
            history.pushState({}, "", "/u/storage/list");
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.note, "Notes", ()=>{
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.settings, "Settings", ()=>{
            history.pushState({}, "", "/u/settings");
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.logout, "Log Out", ()=>{
            //this.attrs.nav.hide()
            api.clearUserToken();
            history.pushState({}, "", "/")
        });
        if (daedalus.platform.isAndroid) {
            this.attrs.nav.addAction(resources.svg['return'], "Reload", ()=>{
                try {
                    Client.reloadPage()
                } catch (e) {
                    console.error(e)
                }
            });
        }

        this.toggleShowMenuFixed();

        this.appendChild(this.attrs.router)
        this.appendChild(this.attrs.nav)
    }

    elementMounted() {

        // TODO: RHS margin is browser and OS Dependant
        // TODO: always show rhs scroll bar

        this.updateMargin()

        // TODO: don't create the Router until after the token
        // is validated
        const token = api.getUsertoken()
        if (!!token) {
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


    handleResize(event) {
        this.toggleShowMenuFixed();
    }

    toggleShowMenuFixed() {
        const condition = document.body.clientWidth > 900

        if (!!this.attrs.nav) {
            this.attrs.nav.showFixed(condition)
        }

        if (!!this.attrs.router) {
            if (condition === true) {
                this.attrs.router.addClassName(style.fullsize)
            } else {
                this.attrs.router.removeClassName(style.fullsize)
            }
        }
    }

    updateMargin() {

        this.addClassName(style.rootWeb)

        //this.attrs.router.updateProps({className: style.margin})
        //console.log(document.body.scrollHeight , window.innerHeight)

        //if (document.body.scrollHeight > window.innerHeight) {
        //    this.attrs.router.updateProps({className: style.margin})
        //} else {
        //    this.attrs.router.updateProps({className: null})
        //}
    }
}


