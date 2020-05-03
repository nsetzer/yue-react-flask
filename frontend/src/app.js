
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
    AuthenticatedRouter
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
    rootWebDesktop: StyleSheet({
        width: 'calc(100vw - 17px)',
        //height: '100vh',
        margin: {left: 0, top: 0, bottom: 0, right: 0},
        padding: 0,
        //background: {color: 'cyan'}
    }),
    rootWebMobile: StyleSheet({
        width: '100vw',
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


class AppRouter extends AuthenticatedRouter {

    isAuthenticated() {
        return api.getUsertoken() !== null
    }
}

export class Root extends DomElement {

    constructor() {
        super("div", {}, []);

        const body = document.getElementsByTagName("BODY")[0];
        body.className = style.body

        this.attrs = {
            main: new pages.LandingPage,
            page_cache: {},
            nav: null,
            router: null,
            container: new DomElement("div", {}, []),
        }

        window.onresize = this.handleResize.bind(this)

    }

    buildRouter() {

        let router = new AppRouter(this.attrs.container)
        router.addAuthRoute("/u/storage/preview/:path*", (cbk)=>this.handleRoute(cbk, pages.StoragePreviewPage), '/login');
        router.addAuthRoute("/u/storage/:mode/:path*", (cbk)=>this.handleRoute(cbk, pages.StoragePage), '/login');
        router.addAuthRoute("/u/fs/:path*", (cbk)=>this.handleRoute(cbk, pages.FileSystemPage), '/login');
        router.addAuthRoute("/u/playlist", (cbk)=>this.handleRoute(cbk, pages.PlaylistPage), '/login');
        router.addAuthRoute("/u/settings", (cbk)=>this.handleRoute(cbk, pages.SettingsPage), '/login');
        router.addAuthRoute("/u/library/list", (cbk)=>this.handleRoute(cbk, pages.LibraryPage), '/login');
        router.addAuthRoute("/u/library/sync", (cbk)=>this.handleRoute(cbk, pages.SyncPage), '/login');
        router.addAuthRoute("/u/radio", (cbk)=>this.handleRoute(cbk, pages.UserRadioPage), '/login');
        router.addAuthRoute("/u/:path*", (cbk)=>{history.pushState({}, "", "/u/storage/list")}, '/login');
        router.addNoAuthRoute("/login", (cbk)=>this.handleRoute(cbk, pages.LoginPage), "/u/storage/list");
        router.addRoute("/p/:path*", (cbk)=>{history.pushState({}, "", "/")});
        router.addRoute("/:path*", (cbk)=>{cbk(this.attrs.main)});
        router.setDefaultRoute((cbk)=>{cbk(this.attrs.main)})
        this.attrs.router = router

        this.attrs.nav = new components.NavMenu();
        this.attrs.nav.addAction(resources.svg.playlist, "Playlist", ()=>{
            history.pushState({}, "", "/u/playlist");
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.music_note, "Library", ()=>{
            history.pushState({}, "", "/u/library/list");
            this.attrs.nav.hide();
        });
        //this.attrs.nav.addAction(resources.svg.externalmedia, "Radio", ()=>{
        //    history.pushState({}, "", "/u/radio");
        //    this.attrs.nav.hide();
        //});
        this.attrs.nav.addAction(resources.svg.download, "Sync", ()=>{
            history.pushState({}, "", "/u/library/sync");
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.documents, "Storage", ()=>{
            history.pushState({}, "", "/u/storage/list");
            this.attrs.nav.hide();
        });
        if (daedalus.platform.isMobile) {
            this.attrs.nav.addAction(resources.svg.documents, "File System", ()=>{
                history.pushState({}, "", "/u/fs");
                this.attrs.nav.hide();
            });
        }
        this.attrs.nav.addAction(resources.svg.note, "Notes", ()=>{
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.settings, "Settings", ()=>{
            history.pushState({}, "", "/u/settings");
            this.attrs.nav.hide();
        });
        this.attrs.nav.addAction(resources.svg.logout, "Log Out", ()=>{
            api.clearUserToken();
            history.pushState({}, "", "/")
        });
        //if (daedalus.platform.isAndroid) {
        //    this.attrs.nav.addAction(resources.svg['return'], "Reload", ()=>{
        //        try {
        //            Client.reloadPage()
        //        } catch (e) {
        //            console.error(e)
        //        }
        //    });
        //}

        this.toggleShowMenuFixed();

        this.appendChild(this.attrs.container)
        this.appendChild(this.attrs.nav)

        // perform the initial route
        this.attrs.router.handleLocationChanged(window.location.pathname)
        // handle future location changes
        this.connect(history.locationChanged, this.handleLocationChanged.bind(this))
    }

    handleLocationChanged() {
        this.attrs.router.handleLocationChanged(window.location.pathname)
    }

    handleRoute(fn, page) {
        if (this.attrs.page_cache[page] === undefined) {
            this.attrs.page_cache[page] = new page()
        }
        fn(this.attrs.page_cache[page])
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
        const condition = document.body.clientWidth > 900 && api.getUsertoken() !== null

        if (!!this.attrs.nav) {
            this.attrs.nav.showFixed(condition)
        }

        if (!!this.attrs.container) {
            if (condition === true) {
                this.attrs.container.addClassName(style.fullsize)
            } else {
                this.attrs.container.removeClassName(style.fullsize)
            }
        }
    }

    updateMargin() {

        if (daedalus.platform.isMobile) {
            this.addClassName(style.rootWebMobile)
        } else {
            this.addClassName(style.rootWebDesktop)
        }


        //this.attrs.container.updateProps({className: style.margin})
        //console.log(document.body.scrollHeight , window.innerHeight)

        //if (document.body.scrollHeight > window.innerHeight) {
        //    this.attrs.container.updateProps({className: style.margin})
        //} else {
        //    this.attrs.container.updateProps({className: null})
        //}
    }
}


