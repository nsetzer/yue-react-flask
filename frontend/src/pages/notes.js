
from module daedalus import {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    Router
}
import module api
import module store
import module router
import module components

include './util.js'

const styles = {
    page: StyleSheet({
        width: '100%',
    }),

    list: StyleSheet({
        'padding-left': '1em',
        'padding-right': '1em',
    }),
    item: StyleSheet({
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

    contentDiv: StyleSheet({
        //background-color: '#0000FF33',

        'padding-left': '1em',
        'padding-right': '1em',
    }),

    contentPre: StyleSheet({
        'width': '100%',
        'max-width': '100%',
        overflow-x: 'scroll',
    }),

    contentText: StyleSheet({
        padding: "2px",
        border: "1px solid black",
        'width': 'calc(100% - 6px)',
        // minus header (40), footer (40) and padding (2x16) size
        'height': 'calc(100vh - 80px - 32px)',
        'max-height': 'calc(100vh - 80px - 32px)',
        'max-width': 'calc(100% - 6px)',
        overflow-x: 'scroll',
    }),
}

export class NoteContext {

    constructor(root, base) {
        this.root = root
        this.base = base
        this.cache = {}
    }

    getList() {
        return api.fsNoteList(this.root, this.base)
    }

    getContent(noteId) {

        if (this.cache[noteId] !== undefined) {
            return new Promise((resolve, reject) => {
                resolve(this.cache[noteId])
            })
        } else {
            return new Promise((resolve, reject) => {
                api.fsNoteGetContent(this.root, this.base, noteId, null, null)
                    .then(result=> {
                        this.cache[noteId] = result;
                        resolve(result);
                    })
                    .catch(error => {
                        reject(error);
                    })
            })
        }

    }

    setContent(noteId, content) {
        this.cache[noteId] = content;

        return api.fsNoteSetContent(this.root, this.base, noteId, content, null, null)

    }
}

function initContext() {
    if (store.globals.note_ctxt === undefined) {
        store.globals.note_ctxt = new NoteContext("default", "public/notes")
    }
    return store.globals.note_ctxt
}

class ListHeader extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        this.addAction(resources.svg['menu'], ()=>{
            store.globals.showMenu()
        })

    }
}

class ListFooter extends components.NavFooter {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        //this.addAction(resources.svg['select'], ()=>{})

    }
}

class NotesItem extends DomElement {
    constructor(ctxt, note_id, info) {
        super("div", {className: styles.item}, []);

        this.attrs = {ctxt, note_id, info}
        this.appendChild(new DomElement("div", {}, [new TextElement(info.title)]))

        const t = fmtEpochTime(info.mtime * 1000)
        this.appendChild(new DomElement("div", {}, [new TextElement(`Modified Time: ${t}`)]))


        /*
        items[noteId, info]

        noteId: fileName
        info:
            encryption: "system"
            file_name: "Drills.txt"
            file_path: "public/notes/Drills.txt"
            mtime: 1605487060
            size: 141

        */
    }


    onClick(event) {

        router.navigate(router.routes.userNotesContent({noteId: this.attrs.note_id}, {}))

    }
}

class NotesList extends DomElement {
    constructor(parent, index, song) {
        super("div", {className: styles.list}, []);

    }

    setNotes(ctxt, notes) {
        this.removeChildren()

        const sorted_keys = Object.keys(notes).sort()
        console.log(sorted_keys)
        for (let note_id of sorted_keys) {
            console.log(note_id, notes[note_id])
            let info = notes[note_id]
            this.appendChild(new NotesItem(ctxt, note_id, info))
        }

    }
}

export class NotesPage extends DomElement {
    constructor() {
        super("div", {className: styles.page}, []);

        this.attrs = {
            header: new ListHeader(this),
            footer: new ListFooter(this),
            container: new NotesList(),
            padding1: new DomElement("div", {className: styles.padding1}, []),
            padding2: new DomElement("div", {className: styles.padding2}, []),
        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.padding1)
        this.appendChild(this.attrs.container)
        this.appendChild(this.attrs.padding2)
        this.appendChild(this.attrs.footer)

        this.attrs.ctxt = initContext()

    }

    elementMounted() {
        console.log("mount library view")
        this.attrs.ctxt.getList()
            .then(result => {
                console.log(result.result)
                this.attrs.container.setNotes(this.attrs.ctxt, result.result)
            })
            .catch(error => {
                console.log(error)
            })
    }
}

class ContentHeader extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        this.addAction(resources.svg['menu'], ()=>{
            store.globals.showMenu()
        })

        this.addAction(resources.svg['return'], ()=>{
            router.navigate(router.routes.userNotesList({}, {}))
        })

        this.addAction(resources.svg['edit'], ()=>{

            router.navigate(router.routes.userNotesEdit({
                noteId: this.attrs.parent.state.match.noteId}, {}))

        })

    }
}

class ContentFooter extends components.NavFooter {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        //this.addAction(resources.svg['select'], ()=>{})

    }
}

export class NoteContentPage extends DomElement {
    constructor() {
        super("div", {className: styles.page}, []);

        this.attrs = {
            header: new ContentHeader(this),
            footer: new ContentFooter(this),
            container: new DomElement("div", {className: styles.contentDiv}, []),
            padding1: new DomElement("div", {className: styles.padding1}, []),
            padding2: new DomElement("div", {className: styles.padding2}, []),
        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.padding1)
        this.appendChild(this.attrs.container)
        this.appendChild(this.attrs.padding2)
        this.appendChild(this.attrs.footer)

        this.attrs.ctxt = initContext()

    }

    elementMounted() {
        this.showContent()
    }

    showContent() {
        this.attrs.container.removeChildren()

        this.attrs.ctxt.getContent(this.state.match.noteId)
            .then(result => {

                this.attrs.container.appendChild(new DomElement("pre", {className: styles.contentPre}, [
                    new TextElement(result + "\n\n\n")]))
                //this.attrs.container.appendChild(new components.VSpacer("3em"))
            })
            .catch(error => {
                console.log(error)
            })
    }

    beginEdit() {

        this.attrs.container.removeChildren()

        this.attrs.ctxt.getContent(this.state.match.noteId)
            .then(result => {

                this.attrs.container.appendChild(new DomElement("textarea", {className: styles.contentText}, [
                    new TextElement(result)]))
                //this.attrs.container.appendChild(new components.VSpacer("3em"))
            })
            .catch(error => {
                console.log(error)
            })
    }


}

class EditHeader extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        this.addAction(resources.svg['menu'], ()=>{
            store.globals.showMenu()
        })

        this.addAction(resources.svg['discard'], ()=>{
            router.navigate(router.routes.userNotesContent({
                noteId: this.attrs.parent.state.match.noteId}, {}))

        })

        this.addAction(resources.svg['save'], ()=>{

            const noteId = this.attrs.parent.state.match.noteId
            const nd = this.attrs.parent.attrs.textarea.getDomNode()
            console.log(nd.value)

            this.attrs.parent.attrs.ctxt.setContent(
                this.attrs.parent.state.match.noteId, nd.value)
                .then((result)=>{
                    router.navigate(router.routes.userNotesContent(
                        {noteId}, {}))
                })
                .catch((error)=>{

                })


        })

    }
}

class EditFooter extends components.NavFooter {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        //this.addAction(resources.svg['select'], ()=>{})

    }
}

export class NoteEditPage extends DomElement {
    constructor() {
        super("div", {className: styles.page}, []);

        this.attrs = {
            header: new EditHeader(this),
            footer: new EditFooter(this),
            container: new DomElement("div", {className: styles.contentDiv}, []),
            textarea: new DomElement("textarea", {className: styles.contentText}, []),
            padding1: new DomElement("div", {className: styles.padding1}, []),

        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.padding1)
        this.appendChild(this.attrs.container)
        this.appendChild(this.attrs.footer)

        this.attrs.container.appendChild(this.attrs.textarea)

        this.attrs.ctxt = initContext()

    }

    elementMounted() {
        this.showContent()
    }

    showContent() {
        this.attrs.textarea.removeChildren()

        this.attrs.ctxt.getContent(this.state.match.noteId)
            .then(result => {
                this.attrs.textarea.appendChild(new TextElement(result))
            })
            .catch(error => {
                console.log(error)
            })
    }


}