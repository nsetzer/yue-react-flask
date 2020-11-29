
from module daedalus import {
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    TextInputElement,
    Router
}
import module api

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

}

export class NoteContext {

    constructor(root, base) {
        this.root = root
        this.base = base
    }

    getList() {
        return api.fsNoteList(this.root, this.base)
    }

    getContent(note_id) {

        return api.fsNoteGetContent(this.root, this.base, note_id, null, null)

    }
}

class Header extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        this.addAction(resources.svg['menu'], ()=>{
            store.globals.showMenu()
        })

        this.addAction(resources.svg['media_prev'], ()=>{
            audio.AudioDevice.instance().prev()
        })

    }

}

class Footer extends components.NavFooter {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        this.addAction(resources.svg['select'], ()=>{
        })

        this.addAction(resources.svg['media_shuffle'], ()=>{
        })

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
        console.log("click")

        this.attrs.ctxt.getContent(this.attrs.note_id)
            .then(result => {
                console.log(result)
            })
            .catch(error => {
                console.log(error)
            })

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
            header: new Header(this),
            footer: new Footer(this),
            container: new NotesList(),
            padding1: new DomElement("div", {className: styles.padding1}, []),
            padding2: new DomElement("div", {className: styles.padding2}, []),
        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.padding1)
        this.appendChild(this.attrs.container)
        this.appendChild(this.attrs.padding2)
        this.appendChild(this.attrs.footer)

        this.attrs.ctxt = new NoteContext("default", "public/notes")

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