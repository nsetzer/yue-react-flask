
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
}

// --

class ArtistTreeItem extends components.TreeItem {

    constructor(parent, obj, selectMode=1) {
        super(parent, 0, obj.name, obj, selectMode);

    }

    buildChildren(obj) {
        return obj.albums.map(album => new AlbumTreeItem(this, album, this.attrs.selectMode))
    }
}

class AlbumTreeItem extends components.TreeItem {

    constructor(parent, obj, selectMode=1) {
        super(parent, 1, obj.name, obj, selectMode);
    }

    buildChildren(obj) {
        return obj.tracks.map(track => new TrackTreeItem(this, track, this.attrs.selectMode))
    }
}

class TrackTreeItem extends components.TreeItem {

    constructor(parent, obj, selectMode=1) {
        let selected = false
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
        console.log(this)
        this.attrs.container.children.forEach(child => {
            this._chkArtistSelection(result, child)
        })

        return result
    }

    _chkArtistSelection(result, node) {
        if (!node.attrs.children) {
            if (node.isSelected()) {
                this._collectArtist(result, node.attrs.obj)
            }
            return;
        }
        node.attrs.children.forEach(child => {
            this._chkAlbumSelection(result, child, node.attrs.obj.name)
        })

    }

    _collectArtist(result, obj) {
        obj.albums.forEach(child => {
            this._collectAlbum(result, child, obj.name)
        })
    }

    _chkAlbumSelection(result, node, artist) {
        if (!node.attrs.children) {
            if (node.isSelected()) {
                this._collectAlbum(result, node.attrs.obj, artist)
            }
            return;
        }
        node.attrs.children.forEach(child => {
            this._chkTrackSelection(result, child, artist, node.attrs.obj.name)
        })
    }

    _collectAlbum(result, obj, artist) {
        obj.tracks.forEach(child => {
            this._collectTrack(result, child, artist, obj.name)
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
                result.push(song)
            }
        }

    }

    /**
    collect a track when the node does not exist
    and a parent, which exists, is selected
    */
    _collectTrack(result, obj, artist, album) {

        if (this.attrs.selectMode == components.TreeItem.SELECTION_MODE_CHECK) {
            if (obj.sync == 0) {
                const track = {"uid": obj.id, "spk": obj.spk, sync: 1}
                result.push(track)
            }
        } else {
            const song = {...obj, artist, album}
            result.push(song)
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
        api.librarySearchForest(text)
                .then(result => {
                    this.attrs.view.reset()
                    result.result.forEach(tree => {
                        this.attrs.view.addItem(new ArtistTreeItem(this, tree))
                    })
                })
                .catch(error => {
                    console.log(error);
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
        console.log("mount library view")

        if (this.attrs.firstMount) {
            this.attrs.firstMount = false
            this.search("")
        }

        if (daedalus.platform.isAndroid) {
            registerAndroidEvent('onfetchprogress', this.handleFetchProgress.bind(this))
            registerAndroidEvent('onfetchcomplete', this.handleFetchComplete.bind(this))
        }

    }

    elementUnmounted() {

    }

    handleHideFileMore() {

    }

    search(text) {
        if (daedalus.platform.isAndroid) {

            let text = AndroidNativeAudio.buildForest();
            let forest = JSON.parse(text);

            this.attrs.view.reset()
            this.attrs.view.setForest(forest);

        } else {
            api.librarySearchForest(text)
                .then(result => {
                    this.attrs.view.reset()
                    this.attrs.view.setForest(result.result);
                })
                .catch(error => {
                    console.log(error);
                })
        }
    }

    handleSyncSave() {


        let songs = this.attrs.view.getSelectedSongs()

        let data = {}
        for (let i=0; i < songs.length; i++) {
            let song = songs[i];
            data[song.spk]=song.sync;
        }

        if (daedalus.platform.isAndroid) {
            let payload = JSON.stringify(data);
            AndroidNativeAudio.updateSyncStatus(payload)
        } else {
            console.log(data)
        }

    }

    handleFetchProgress(payload) {
        console.log("fetch progress: " + JSON.stringify(payload))

        this.attrs.header.updateStatus(`${payload.count}/${payload.total}`);
    }

    handleFetchComplete(payload) {
        console.log("fetch complete: " + JSON.stringify(payload))
    }

    showMore(item) {
        console.log("on show more clicked");
    }
}