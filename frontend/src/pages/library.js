
/*
todo: Tree Items need a two state check status
        0/1 : original check state
        0/1 : item check state after modified by the user
    A button to reset the check state for all levels
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
import module components
import module audio
import module store
import module router

class SearchBannishedCheckBox extends components.CheckBoxElement {

    // TODO: this is a framework bug: inherited signals are not bound
    onClick(event) {
        this.attrs.callback()
    }

    getStateIcons() {
        return [
            resources.svg.checkbox_unchecked,
            resources.svg.checkbox_checked,
        ];
    }

}

class SearchModeCheckBox extends components.CheckBoxElement {

    // TODO: this is a framework bug: inherited signals are not bound
    onClick(event) {
        this.attrs.callback()
    }

    getStateIcons() {
        return [
            resources.svg.checkbox_unchecked,
            resources.svg.checkbox_synced,
            resources.svg.checkbox_not_synced,
            resources.svg.checkbox_partial,
        ];
    }

}

class SyncCheckBox extends components.CheckBoxElement {


    // TODO: this is a framework bug: inherited signals are not bound
    onClick(event) {
        this.attrs.callback()
    }


    getStateIcons() {
        return [
            resources.svg.checkbox_unchecked,
            resources.svg.checkbox_download,
            resources.svg.checkbox_partial,
        ];
    }

}


const style = {
    main: StyleSheet({
        width: '100%',
    }),

    grow: StyleSheet({
        'flex-grow': 1,
    }),

    viewPad: StyleSheet({'padding-left': '1em', 'padding-right': '1em'}),

    listItemCheck: StyleSheet({
        //padding-left:'.5em',
        //padding-right:'.5em',
        'cursor': 'pointer',
        //'border': 'solid 1px black'
    }),



    savedSearchPage: StyleSheet({
        width: '100%',
    }),
    savedSearchList: StyleSheet({
        'padding-left': '1em',
        'padding-right': '1em',
    }),
    savedSearchItem: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        margin-bottom: '.25em',
        border: {style: "solid", width: "1px"},
        width: 'calc(100% - 2px)', // minus border width * 2
    }),
    padding1: StyleSheet({
        height: '1em',
        'min-height': '1em'
    }),
    padding2: StyleSheet({
        height: '33vh',
        'min-height': '64px'
    }),

}

function shuffle(a) {
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

class Header extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent
        this.attrs.txtInput = new TextInputElement("", null, () => {
                this.attrs.parent.search(this.attrs.txtInput.props.value)
        })

        this.attrs.txtInput.updateProps({"autocapitalize": "off"})

        this.addAction(resources.svg['menu'], ()=>{
            store.globals.showMenu()
        })

        this.addAction(resources.svg['media_prev'], ()=>{
            audio.AudioDevice.instance().prev()
        })

        this.addAction(resources.svg['media_play'], ()=>{
            audio.AudioDevice.instance().togglePlayPause()
        })

        this.addAction(resources.svg['media_next'], ()=>{
            audio.AudioDevice.instance().next()
        })

        this.addRow(false)
        this.addRowElement(0, this.attrs.txtInput)
        this.attrs.txtInput.addClassName(style.grow)

        if (daedalus.platform.isAndroid) {

            this.attrs.chk = new SearchModeCheckBox(this.handleCheck.bind(this), 1);

            this.addRowElement(0, new components.HSpacer("1em"));
            this.addRowElement(0, this.attrs.chk);
            this.addRowElement(0, new components.HSpacer("1em"));
        }

        this.attrs.show_banished = new SearchBannishedCheckBox(this.handleCheckShowBannished.bind(this), 0);
        this.addRowElement(0, new components.HSpacer("1em"));
        this.addRowElement(0, this.attrs.show_banished);
        this.addRowElement(0, new components.HSpacer("1em"));

        this.addRowAction(0, resources.svg['search'], ()=>{
            this.attrs.parent.search(this.attrs.txtInput.props.value)
        })

        /*
        this.addRowAction(0, resources.svg['media_shuffle'], ()=>{

            const songList = this.attrs.parent.attrs.view.getSelectedSongs()
            console.log("creating playlist", songList.length)
            audio.AudioDevice.instance().queueSet(shuffle(songList).splice(0, 100))
            audio.AudioDevice.instance().next()

            this.attrs.parent.attrs.view.selectAll(false)

        })

        this.addRowAction(0, resources.svg['select'], ()=>{

            const count = this.attrs.parent.attrs.view.countSelected()
            console.log(count)
            this.attrs.parent.attrs.view.selectAll(count == 0)

        })*/

    }

    setQuery(query) {
        this.attrs.txtInput.setText(query)
    }

    handleCheck() {
        this.attrs.chk.setCheckState((this.attrs.chk.attrs.checkState + 1)%3)
    }

    handleCheckShowBannished() {
        this.attrs.show_banished.setCheckState((this.attrs.show_banished.attrs.checkState + 1)%2)
    }

    syncState() {
        return this.attrs.chk.attrs.checkState;
    }


    showBanished() {
        return this.attrs.show_banished.attrs.checkState;
    }
}

class Footer extends components.NavFooter {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        this.addAction(resources.svg['select'], ()=>{

            const count = this.attrs.parent.attrs.view.countSelected()
            this.attrs.parent.attrs.view.selectAll(count == 0)

        })

        this.addAction(resources.svg['media_shuffle'], ()=>{

            const songList = this.attrs.parent.attrs.view.getSelectedSongs()
            console.log("creating playlist", songList.length)
            audio.AudioDevice.instance().queueSet(shuffle(songList).splice(0, 100))
            audio.AudioDevice.instance().next()

            this.attrs.parent.attrs.view.selectAll(false)

        })

    }
}
// --

// --

class ArtistTreeItem extends components.TreeItem {

    constructor(parent, obj, selectMode=1) {
        // TODO: this is a bug in the forest builder on AndroidNativeAudio
        // it will set a 'selected' fields always -- based on whether
        // or no the tracks are synced. it should not do this
        // when running a general search
        let selected = 0
        if (selectMode==components.TreeItem.SELECTION_MODE_CHECK) {
            selected = obj.selected||0
        }
        super(parent, 0, obj.name, obj, selectMode, selected);

    }

    buildChildren(obj) {
        return obj.albums.map(album => new AlbumTreeItem(this, album, this.attrs.selectMode))
    }

    constructCheckbox(callback, initialState) {
        return new SyncCheckBox(callback, initialState)
    }
}

class AlbumTreeItem extends components.TreeItem {

    constructor(parent, obj, selectMode=1) {
        let selected = 0
        if (selectMode==components.TreeItem.SELECTION_MODE_CHECK) {
            selected = obj.selected||0
        }
        super(parent, 1, obj.name, obj, selectMode, selected);
    }

    buildChildren(obj) {
        return obj.tracks.map(track => new TrackTreeItem(this, track, this.attrs.selectMode))
    }

    constructCheckbox(callback, initialState) {
        return new SyncCheckBox(callback, initialState)
    }
}

class TrackTreeItem extends components.TreeItem {

    constructor(parent, obj, selectMode=1) {
        let selected = 0
        if (selectMode == components.TreeItem.SELECTION_MODE_CHECK) {
            selected = obj.sync || 0
        }
        super(parent, 2, obj.title, obj, selectMode, selected);

        this.setMoreCallback(this.handleMoreClicked.bind(this))

    }

    hasChildren() {
        return false;
    }

    handleMoreClicked() {
        const abm = this.attrs.parent
        const art = abm.attrs.parent
        const view = art.attrs.parent
        const page = view.attrs.parent

        const song = {...this.attrs.obj,
            artist: art.attrs.obj.name,
            album: abm.attrs.obj.name
        }
        console.log(art.attrs.parent)
        page.showMore(song)
    }

    constructCheckbox(callback, initialState) {
        return new SyncCheckBox(callback, initialState)
    }
}

class LibraryTreeView extends components.TreeView {

    constructor(parent, selectMode) {
        super();
        this.attrs.parent = parent
        this.attrs.selectMode = selectMode
    }

    setForest(forest) {
        forest.forEach(tree => {
            this.addItem(new ArtistTreeItem(this, tree, this.attrs.selectMode))
        })
    }

    getSelectedSongs() {

        const result = []
        this.attrs.container.children.forEach(child => {
            this._chkArtistSelection(result, child)
        })

        return result
    }

    _chkArtistSelection(result, node) {
        if (!node.attrs.children) {
            this._collectArtist(result, node.attrs.obj, node.isSelected())
            return;
        }
        node.attrs.children.forEach(child => {
            this._chkAlbumSelection(result, child, node.attrs.obj.name)
        })

    }

    _collectArtist(result, obj, selected) {
        obj.albums.forEach(child => {
            this._collectAlbum(result, child, obj.name, selected)
        })
    }

    _chkAlbumSelection(result, node, artist) {
        if (!node.attrs.children) {
            this._collectAlbum(result, node.attrs.obj, artist, node.isSelected())
            return;
        }
        node.attrs.children.forEach(child => {
            this._chkTrackSelection(result, child, artist, node.attrs.obj.name)
        })
    }

    _collectAlbum(result, obj, artist, selected) {
        obj.tracks.forEach(child => {
            this._collectTrack(result, child, artist, obj.name, selected)
        })
    }

    /**
    collect a track when the node exists and is selected
    */
    _chkTrackSelection(result, node, artist, album) {

        if (this.attrs.selectMode == components.TreeItem.SELECTION_MODE_CHECK) {


            const item = node.attrs.obj;

            if (item.sync == 1 && node.attrs.selected == 0) {
                const track = {"spk": item.spk, sync: 0}
                result.push(track)
            }

            else if (item.sync == 0 && node.attrs.selected == 1) {
                const track = {"spk": item.spk, sync: 1}
                result.push(track)
            }
        } else {
            if (node.isSelected()) {
                const song = {...node.attrs.obj, artist, album}
                console.log(JSON.stringify(song));
                result.push(song)
            }
        }

    }

    /**
    collect a track when the node does not exist
    and a parent, which exists, is selected

    TODO: the optimization to use is: was this or a parent
    modified by the user, if not then dont descend.
    */
    _collectTrack(result, obj, artist, album, selected) {

        if (this.attrs.selectMode == components.TreeItem.SELECTION_MODE_CHECK) {
            if (obj.sync == 0 && selected == 1) {
                const track = {"uid": obj.id, "spk": obj.spk, sync: 1}
                result.push(track)
            }

            if (obj.sync == 1 && selected == 0) {
                const track = {"uid": obj.id, "spk": obj.spk, sync: 0}
                result.push(track)
            }

        } else {
            if (selected) {
                const song = {...obj, artist, album}
                result.push(song)
            }
        }

    }
}

export class LibraryPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            header: new Header(this),
            footer: new Footer(this),
            view: new LibraryTreeView(this, components.TreeItem.SELECTION_MODE_HIGHLIGHT),
            more: new components.MoreMenu(this.handleHideFileMore.bind(this)),
            more_context_item: null,
            firstMount: true,
            currentSearch: null,
        }

        this.attrs.view.addClassName(style.viewPad)
        this.attrs.more.addAction("Add To Queue", this.handleAddToQueue.bind(this))

        this.appendChild(this.attrs.more)
        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.view)
        this.appendChild(this.attrs.footer)


    }

    elementMounted() {
        console.log("mount library view")

        // this works around an android native bug, where the query
        // sometimes gets passed in as "undefined"
        let query = daedalus.util.parseParameters()['query']
        if (query === null || query === undefined) {
            query = ""
        } else {
            query = "" + query
        }

        if (this.attrs.firstMount || (this.attrs.currentSearch !== query)) {
            this.attrs.firstMount = false
            this.attrs.header.setQuery(query)
            this.search(query)
        }

    }


    search(text) {
        this.attrs.view.reset()

        this.attrs.currentSearch = text
        router.navigate(router.routes.userLibraryList({}, {query: text}))

        this.attrs.search_promise = new Promise((accept, reject) => {

            let showBanished = this.attrs.header.showBanished()===1; //to bool
            console.log(showBanished)

            if (daedalus.platform.isAndroid) {

                let syncState = this.attrs.header.syncState();
                let payload = AndroidNativeAudio.buildForest(text, syncState, showBanished);
                let forest = JSON.parse(payload);

                this.attrs.view.setForest(forest);

            } else {
                api.librarySearchForest(text, showBanished)
                    .then(result => {
                        this.attrs.view.setForest(result.result);
                    })
                    .catch(error => {
                        console.log(error);
                    })
            }
            accept();
        })

    }

    showMore(item) {
        this.attrs.more_context_item = item
        this.attrs.more.show()

    }

    handleHideFileMore() {

        this.attrs.more.hide()
    }

    handleAddToQueue() {

        audio.AudioDevice.instance().queuePlayNext(this.attrs.more_context_item)

        //api.librarySong(this.attrs.more_context_item.id)
        //    .then(result => {
        //        console.log()
        //        audio.AudioDevice.instance().queuePlayNext(result.result)
        //    })
        //    .catch(error => {
        //        console.error(error)
        //    })

    }
}

class SyncHeader extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent
        this.attrs.txtInput = new TextInputElement("", null, () => {
                this.attrs.parent.search(this.attrs.txtInput.props.value)
        })

        this.attrs.txtInput.updateProps({"autocapitalize": "off"})

        this.attrs.status = new components.MiddleText("...");

        this.addAction(resources.svg['menu'], ()=>{
            store.globals.showMenu()
        })

        this.addAction(resources.svg['media_error'], ()=>{
            if (daedalus.platform.isAndroid) {
                AndroidNativeAudio.cancelTask();
            }
        })

        this.addAction(resources.svg['sort'], ()=>{
            if (daedalus.platform.isAndroid) {
                AndroidNativeAudio.beginFetch("" + api.getAuthToken());
            }
        })

        this.addAction(resources.svg['search_generic'], ()=>{
                this.attrs.parent.search();
        })

        this.addAction(resources.svg['save'], ()=>{
            this.attrs.parent.handleSyncSave();
        })

        this.addAction(resources.svg['download'], ()=>{
            if (daedalus.platform.isAndroid) {
                AndroidNativeAudio.beginSync("" + api.getAuthToken());
            }
        })

        this.addRow(false)
        this.addRowElement(0, this.attrs.txtInput)
        this.attrs.txtInput.addClassName(style.grow)

        if (daedalus.platform.isAndroid)
        {

            this.attrs.chk = new SearchModeCheckBox(this.handleCheck.bind(this), 0);

            this.addRowElement(0, new components.HSpacer("1em"));
            this.addRowElement(0, this.attrs.chk);
            this.addRowElement(0, new components.HSpacer("1em"));
        }

        this.addRowAction(0, resources.svg['search'], ()=>{
            this.attrs.parent.search(this.attrs.txtInput.props.value)
        })

        this.addRow(false)
        this.addRowElement(1, this.attrs.status)
    }

    updateStatus(text) {
        this.attrs.status.setText(text)

    }

    searchText() {
        return this.attrs.txtInput.props.value
    }

    handleCheck() {
        this.attrs.chk.setCheckState((this.attrs.chk.attrs.checkState + 1)%3)
    }

    syncState() {
        return this.attrs.chk.attrs.checkState;
    }

}

class SyncFooter extends components.NavFooter {
    constructor(parent) {
        super();

        this.attrs.parent = parent

    }
}

export class SyncPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            header: new SyncHeader(this),
            footer: new SyncFooter(this),
            view: new LibraryTreeView(this, components.TreeItem.SELECTION_MODE_CHECK),
            more: new components.MoreMenu(this.handleHideFileMore.bind(this)),
            more_context_item: null,
            firstMount: true,
        }

        this.attrs.view.addClassName(style.viewPad)
        this.attrs.more.addAction("Add To Queue", () => {})

        this.appendChild(this.attrs.more)
        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.view)
        this.appendChild(this.attrs.footer)

        this.attrs.footer_lbl1 = this.attrs.footer.addText("")

    }

    elementMounted() {
        console.log("mount sync view")

        if (this.attrs.firstMount) {
            this.attrs.firstMount = false
            this.search("")
        }

        if (daedalus.platform.isAndroid) {

            registerAndroidEvent('onfetchprogress', this.handleFetchProgress.bind(this))
            registerAndroidEvent('onfetchcomplete', this.handleFetchComplete.bind(this))
            registerAndroidEvent('onsyncstatusupdated', this.handleSyncStatusUpdated.bind(this))

            registerAndroidEvent('onsyncprogress', this.handleSyncProgress.bind(this))
            registerAndroidEvent('onsynccomplete', this.handleSyncComplete.bind(this))

            registerAndroidEvent('onresume', this.handleResume.bind(this))

            this.updateInfo()

        }

    }

    elementUnmounted() {
        console.log("unmount sync view")
        if (daedalus.platform.isAndroid) {
            registerAndroidEvent('onfetchprogress', ()=>{})
            registerAndroidEvent('onfetchcomplete', ()=>{})
            registerAndroidEvent('onsyncstatusupdated', ()=>{})

            registerAndroidEvent('onsyncprogress', ()=>{})
            registerAndroidEvent('onsynccomplete', ()=>{})

            registerAndroidEvent('onresume', ()=>{})
        }
    }

    handleHideFileMore() {

    }

    search(text) {
        this.attrs.view.reset()

        this.attrs.search_promise = new Promise((accept, reject) => {

            if (daedalus.platform.isAndroid) {

                let syncState = this.attrs.header.syncState();
                let showBanished = false;
                let payload = AndroidNativeAudio.buildForest(text, syncState, showBanished);
                let forest = JSON.parse(payload);

                this.attrs.view.setForest(forest);

            } else {
                let showBanished = false;
                api.librarySearchForest(text, showBanished)
                    .then(result => {
                        this.attrs.view.setForest(result.result);
                    })
                    .catch(error => {
                        console.log(error);
                    })
            }
            accept();
        })
    }

    handleSyncSave() {


        let items = this.attrs.view.getSelectedSongs()

        console.log(JSON.stringify(items))
        console.log(`selected ${items.length} items`)
        let data = {}
        for (let i=0; i < items.length; i++) {
            let item = items[i];
            data[item.spk] = item.sync;
        }

        console.log(JSON.stringify(data))
        console.log(`selected ${data.length} items`)

        if (items.length > 0) {
            if (daedalus.platform.isAndroid) {
                let payload = JSON.stringify(data);

                AndroidNativeAudio.updateSyncStatus(payload)

                //this.search("");  // TODO: fix query
            } else {
                console.log(data)
            }
        } else {
            console.log("sync save: nothing to save")
        }

    }

    handleFetchProgress(payload) {
        this.attrs.header.updateStatus(`${payload.count}/${payload.total}`);
    }

    handleFetchComplete(payload) {
        console.log("fetch complete: " + JSON.stringify(payload))

        this.updateInfo()
    }

    handleSyncProgress(payload) {
        this.attrs.header.updateStatus(`${payload.index}/${payload.total} ${payload.message}`);
    }

    handleSyncComplete(payload) {
        console.log("fetch complete: " + JSON.stringify(payload))
        this.attrs.header.updateStatus("sync complete");

        this.updateInfo()
    }


    handleSyncStatusUpdated(payload) {
        this.search(this.attrs.header.searchText())
    }

    handleResume(payload) {
        console.log("app resumed from js")
        if (daedalus.platform.isAndroid) {
            // TODO: only query when onResume and the JS thinks its still in progress
            AndroidNativeAudio.syncQueryStatus();
        }
    }

    showMore(item) {
        console.log("on show more clicked");
    }

    updateInfo() {
        if (daedalus.platform.isAndroid) {
            const info = JSON.parse(AndroidNativeAudio.getSyncInfo())
            this.attrs.footer_lbl1.setText(`records: ${info.record_count} synced: ${info.synced_tracks}`)
        }
    }
}

class SavedSearchHeader extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        this.addAction(resources.svg['menu'], ()=>{
            store.globals.showMenu()
        })

    }

}

class SavedSearchItem extends DomElement {
    constructor(name, query) {
        super("div", {className: style.savedSearchItem}, []);

        this.attrs = {name, query}
        this.appendChild(new DomElement("div", {}, [new TextElement(name)]))
        this.appendChild(new DomElement("div", {}, [new TextElement(query)]))
    }


    onClick(event) {

        router.navigate(router.routes.userLibraryList({}, {query: this.attrs.query}))

    }
}

const savedSearches = [
    {name: "stoner best", query: "stoner rating >= 5"},
    {name: "grunge best", query: "grunge rating >= 5"},
    {name: "visual best", query: "\"visual kei\" rating >= 5"},
    {name: "english best", query: "language = english rating >= 5"},
    {name: "stone temple pilots", query: "\"stone temple pilots\""},
    {name: "soundwitch", query: "soundwitch"},
    {name: "Gothic Emily", query: "\"gothic emily\""},
]

class SavedSearchList extends DomElement {
    constructor(parent, index, song) {
        super("div", {className: style.savedSearchList}, []);

        for (let i=0; i < savedSearches.length; i++) {
            let s = savedSearches[i]
            this.appendChild(new SavedSearchItem(s.name, s.query))
        }

    }
}

export class SavedSearchPage extends DomElement {
    constructor() {
        super("div", {className: style.savedSearchPage}, []);

        this.attrs = {
            device: audio.AudioDevice.instance(),
            header: new SavedSearchHeader(this),
            container: new SavedSearchList(),
            padding1: new DomElement("div", {className: style.padding1}, []),
            padding2: new DomElement("div", {className: style.padding2}, []),
        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.padding1)
        this.appendChild(this.attrs.container)
        this.appendChild(this.attrs.padding2)
    }
}