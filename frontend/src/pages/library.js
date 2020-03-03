import daedalus with {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    TextInputElement,
    Router
}
import api
import components

const style = {
    main: StyleSheet({
        width: '100%',
    }),

    header: StyleSheet({
        'text-align': 'center',
        'position': 'sticky',
        'background': '#238e23',
        'padding-left': '2em',
        'padding-right': '2em',
        top:0
    }),



}


class Header extends DomElement {
    constructor(parent) {
        super("div", {className: style.header}, []);

        this.appendChild(new components.MiddleText("Library"))
    }
}


// --

class ArtistTreeItem extends components.TreeItem {

    constructor(obj) {
        super(0, obj.name, obj);
    }

    buildChildren(obj) {
        return obj.albums.map(album => new AlbumTreeItem(album))
    }
}

class AlbumTreeItem extends components.TreeItem {

    constructor(obj) {
        super(1, obj.name, obj);
    }

    buildChildren(obj) {
        return obj.tracks.map(track => new TrackTreeItem(track))
    }
}

class TrackTreeItem extends components.TreeItem {

    constructor(obj) {
        super(2, obj.title, obj);
    }

    hasChildren() {
        return false;
    }
}

export class LibraryPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            header: new Header(this),
            container: new components.TreeView("div", {}, [])
        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.container)

    }

    elementMounted() {
        console.log("mount library view")

        api.librarySearchForest("")
            .then(result => {
                this.attrs.container.reset()
                result.result.forEach(tree => {
                    this.attrs.container.addItem(new ArtistTreeItem(tree))
                })
            })
            .catch(error => {
                console.log(error);
            })

    }

}