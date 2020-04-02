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

    constructor(parent, obj) {
        super(0, obj.name, obj);
        this.attrs.parent = parent
    }

    buildChildren(obj) {
        return obj.albums.map(album => new AlbumTreeItem(this, album))
    }
}

class AlbumTreeItem extends components.TreeItem {

    constructor(parent, obj) {
        super(1, obj.name, obj);
        this.attrs.parent = parent
    }

    buildChildren(obj) {
        return obj.tracks.map(track => new TrackTreeItem(this, track))
    }
}

class TrackTreeItem extends components.TreeItem {

    constructor(parent, obj) {
        super(2, obj.title, obj);
        this.attrs.parent = parent

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

    _chkTrackSelection(result, node, artist, album) {
        if (node.isSelected()) {
            const song = {...node.attrs.obj, artist, album}
            result.push(song)
        }
    }

    _collectTrack(result, obj, artist, album) {
        const song = {...obj, artist, album}
        result.push(song)
    }
}

export class LibraryPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            header: new Header(this),
            view: new LibraryTreeView(),
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