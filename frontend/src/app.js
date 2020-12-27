
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
import module components
import module pages
import module resources
import module router
import module store

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
    fullsize: StyleSheet({'margin-left': "300px"}),
    show: StyleSheet({}),
    hide: StyleSheet({display: "none"})
}

function buildRouter(parent, container) {

    const u = router.route_urls;

    let rt = new router.AppRouter(container)

    rt.addAuthRoute(u.userStoragePreview, (cbk)=>parent.handleRoute(cbk, pages.StoragePreviewPage), '/login');
    rt.addAuthRoute(u.userStorage, (cbk)=>parent.handleRoute(cbk, pages.StoragePage), '/login');
    rt.addAuthRoute(u.userFs, (cbk)=>parent.handleRoute(cbk, pages.FileSystemPage), '/login');
    rt.addAuthRoute(u.userPlaylist, (cbk)=>parent.handleRoute(cbk, pages.PlaylistPage), '/login');
    rt.addAuthRoute(u.userSettings, (cbk)=>parent.handleRoute(cbk, pages.SettingsPage), '/login');
    rt.addAuthRoute(u.userNotesEdit, (cbk)=>parent.handleRoute(cbk, pages.NoteEditPage), '/login');
    rt.addAuthRoute(u.userNotesContent, (cbk)=>parent.handleRoute(cbk, pages.NoteContentPage), '/login');
    rt.addAuthRoute(u.userNotesList, (cbk)=>parent.handleRoute(cbk, pages.NotesPage), '/login');
    rt.addAuthRoute(u.userLibraryList, (cbk)=>parent.handleRoute(cbk, pages.LibraryPage), '/login');
    rt.addAuthRoute(u.userLibrarySync, (cbk)=>parent.handleRoute(cbk, pages.SyncPage), '/login');
    rt.addAuthRoute(u.userLibrarySavedSearch, (cbk)=>parent.handleRoute(cbk, pages.SavedSearchPage), '/login');
    rt.addAuthRoute(u.userRadio, (cbk)=>parent.handleRoute(cbk, pages.UserRadioPage), '/login');

    rt.addAuthRoute(u.userWildCard, (cbk)=>{history.pushState({}, "", "/u/storage/list")}, '/login');
    rt.addNoAuthRoute(u.login, (cbk)=>parent.handleRoute(cbk, pages.LoginPage), "/u/library/list");
    rt.addAuthRoute(u.apiDoc, (cbk)=>parent.handleRoute(cbk, pages.OpenApiDocPage), "/login");
    rt.addRoute(u.publicFile, (cbk)=>{parent.handleRoute(cbk, pages.PublicFilePage)});
    rt.addRoute(u.wildCard, (cbk)=>{parent.handleRoute(cbk, pages.LandingPage)});

    rt.setDefaultRoute((cbk)=>{parent.handleRoute(cbk, pages.LandingPage)})

    return rt

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

    doNavigate(res_path) {
        //if (daedalus.platform.isAndroid) {
        if (!this.attrs.nav.isFixed()) {
            //this.attrs.router.clear()
            // call on a timeout to let the menu animation complete smoothly
            // animation is .5s as defined in the NavMenu style
            setTimeout(()=>{
                history.pushState({}, "", res_path);
                window.scrollTo(0,0);
                console.log("scrolled")
            }, 500);
        } else {
            history.pushState({}, "", res_path);
            window.scrollTo(0,0);
            console.log("scrolled")
        }
        this.attrs.nav.hide();
    }

    buildRouter() {

        this.attrs.router = buildRouter(this, this.attrs.container)

        this.attrs.nav = new components.NavMenu();

        store.globals.showMenu = () => {this.attrs.nav.show();}

        this.attrs.nav.addAction(resources.svg.music_note, "Playlist", ()=>{

            this.doNavigate("/u/playlist")
            //history.pushState({}, "", "/u/playlist");

            //this.attrs.router.clear()
            //setTimeout(()=>{history.pushState({}, "", "/u/playlist");}, 500);

            //this.attrs.nav.hide();
        });

        this.attrs.nav.addAction(resources.svg.playlist, "Library", ()=>{
            this.doNavigate("/u/library/list")
            //history.pushState({}, "", "/u/library/list");
            //this.attrs.nav.hide();
        });

        this.attrs.nav.addSubAction(resources.svg.bolt, "Dynamic Playlist", ()=>{
            this.doNavigate("/u/library/saved")
        });

        //this.attrs.nav.addAction(resources.svg.externalmedia, "Radio", ()=>{
        //    history.pushState({}, "", "/u/radio");
        //    this.attrs.nav.hide();
        //});

        if (daedalus.platform.isAndroid) {
            this.attrs.nav.addSubAction(resources.svg.download, "Sync", ()=>{
                this.doNavigate("/u/library/sync")
            });
        }

        this.attrs.nav.addAction(resources.svg.documents, "Storage", ()=>{
            this.doNavigate("/u/storage/list")
        });

        this.attrs.nav.addSubAction(resources.svg.note, "Notes", ()=>{
            this.doNavigate("/u/notes")
        });

        if (daedalus.platform.isAndroid) {
            this.attrs.nav.addAction(resources.svg.documents, "File System", ()=>{
                this.doNavigate("/u/fs")
            });
        }

        this.attrs.nav.addAction(resources.svg.settings, "Settings", ()=>{
            this.doNavigate("/u/settings")
        });

        this.attrs.nav.addAction(resources.svg.logout, "Log Out", ()=>{
            api.clearUserToken();
            // clear the cache of content
            this.attrs.page_cache = {}
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
        //this.attrs.router.handleLocationChanged(window.location.pathname)
        this.handleLocationChanged()

        // handle future location changes
        this.connect(history.locationChanged, this.handleLocationChanged.bind(this))
    }

    handleLocationChanged() {

        this.toggleShowMenuFixed();

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
                .catch((err) => {
                    console.error(err)
                    if (daedalus.platform.isAndroid) {
                        this.buildRouter()
                    }
                })
        } else {
            this.buildRouter()
        }
    }

    handleResize(event) {
        this.toggleShowMenuFixed();
    }

    toggleShowMenuFixed() {

        if (!this.attrs.nav) {
            return
        }

        let condition = (document.body.clientWidth > 900) && \
            (!!api.getUsertoken())

        if (!location.pathname.startsWith("/u") || location.pathname.startsWith("/u/storage/preview")) {
            this.attrs.nav.addClassName(style.hide)
            this.attrs.nav.removeClassName(style.show)
            condition = false;
        } else {
            this.attrs.nav.addClassName(style.show)
            this.attrs.nav.removeClassName(style.hide)
        }

        this.attrs.nav.showFixed(condition)

        if (!!this.attrs.container) {
            if (!!condition) {
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


