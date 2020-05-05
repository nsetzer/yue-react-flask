
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

const style = {
    main: StyleSheet({
        width: '100%',
    }),

    grow: StyleSheet({
        'flex-grow': 1,
    }),

    viewPad: StyleSheet({'padding-left': '1em', 'padding-right': '1em'}),

    listItemCheck: StyleSheet({
        padding-left:'.5em',
        padding-right:'.5em',
        'cursor': 'pointer',
        'border': 'solid 1px black'
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

        this.addAction(resources.svg['menu'], ()=>{
            console.log("menu clicked")
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
            this.attrs.chk = new CheckedElement(this.handleCheck.bind(this), 1);

            this.addRowElement(0, this.attrs.chk);
        }

        this.addRowAction(0, resources.svg['search'], ()=>{
            this.attrs.parent.search(this.attrs.txtInput.props.value)
        })

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

        })

    }

    handleCheck() {
        this.attrs.chk.setCheckState((this.attrs.chk.attrs.checkState == 0)?1:0)
    }

    isChecked() {
        return this.attrs.chk.attrs.checkState != 0;
    }
}

// --

// TODO: this is copied from treeview
function getCheckResource(state) {
    if (state == 2) { // partial
        return resources.svg.sort
    } else if (state == 1) { // checked
        return resources.svg.download
    }

    return resources.svg.select

}

class CheckedElement extends components.SvgElement {
    constructor(callback, initialCheckState) {

        let res = getCheckResource(initialCheckState)
        super(res, {width: 20, height: 32, className: style.listItemCheck})

        this.attrs = {
            callback,
            checkState: initialCheckState,
            initialCheckState,
        }

    }

    setCheckState(checkState) {
        this.attrs.checkState = checkState
        this.props.src = getCheckResource(checkState);
        this.update();
    }


    onClick(event) {

        this.attrs.callback()
    }
}

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

        const song = {...this.attrs.obj,
            artist: art.attrs.obj.name,
            album: abm.attrs.obj.name
        }

        art.attrs.parent.showMore(song)
    }
}

class LibraryTreeView extends components.TreeView {

    constructor(selectMode) {
        super();
        this.attrs.selectMode = selectMode
    }

    setForest(forest) {
        forest.forEach(tree => {
            this.addItem(new ArtistTreeItem(this, tree, this.attrs.selectMode))
        }
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
            view: new LibraryTreeView(components.TreeItem.SELECTION_MODE_HIGHLIGHT),
            more: new components.MoreMenu(this.handleHideFileMore.bind(this)),
            more_context_item: null,
            firstMount: true,
        }

        this.attrs.view.addClassName(style.viewPad)
        this.attrs.more.addAction("Add To Queue", this.handleAddToQueue.bind(this))

        this.appendChild(this.attrs.more)
        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.view)

    }

    elementMounted() {
        console.log("mount library view")

        if (this.attrs.firstMount) {
            this.attrs.firstMount = false
            this.search("")
        }

    }

    search(text) {
        this.attrs.view.reset()

        this.attrs.search_promise = new Promise((accept, reject) => {
            if (daedalus.platform.isAndroid) {

                let syncedOnly = this.attrs.header.isChecked();
                let payload = AndroidNativeAudio.buildForest(text, syncedOnly);
                let forest = JSON.parse(payload);

                this.attrs.view.setForest(forest);

            } else {
                api.librarySearchForest(text)
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
        this.attrs.status = new components.MiddleText("...");

        this.addAction(resources.svg['menu'], ()=>{
            console.log("menu clicked")
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
        this.addRowElement(0, this.attrs.status)
    }

    updateStatus(text) {
        this.attrs.status.setText(text)

    }
}

export class SyncPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            header: new SyncHeader(this),
            view: new LibraryTreeView(components.TreeItem.SELECTION_MODE_CHECK),
            more: new components.MoreMenu(this.handleHideFileMore.bind(this)),
            more_context_item: null,
            firstMount: true,
        }

        this.attrs.view.addClassName(style.viewPad)
        this.attrs.more.addAction("Add To Queue", () => {})

        this.appendChild(this.attrs.more)
        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.view)

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
        }

    }

    elementUnmounted() {
        console.log("unmount sync view")
        if (daedalus.platform.isAndroid) {
            registerAndroidEvent('onfetchprogress', ()=>{})
            registerAndroidEvent('onfetchcomplete', ()=>{})
            registerAndroidEvent('onsyncstatusupdated', ()=>{})
        }
    }

    handleHideFileMore() {

    }

    search(text) {
        this.attrs.view.reset()

        this.attrs.search_promise = new Promise((accept, reject) => {
            if (daedalus.platform.isAndroid) {

                let payload = AndroidNativeAudio.buildForest(text, false);
                let forest = JSON.parse(payload);

                this.attrs.view.setForest(forest);

            } else {
                api.librarySearchForest(text)
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
    }

    handleSyncProgress(payload) {
        this.attrs.header.updateStatus(`${payload.index}/${payload.total} ${payload.message}`);
    }

    handleSyncComplete(payload) {
        console.log("fetch complete: " + JSON.stringify(payload))
        this.attrs.header.updateStatus("sync complete");
    }


    handleSyncStatusUpdated(payload) {
        this.search("")
    }

    showMore(item) {
        console.log("on show more clicked");
    }
}