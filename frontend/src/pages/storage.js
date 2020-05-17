
/**
SERVER SIDE TODO:
- limit simultaneous transcodes using the task engine
  each request submits a task and waits until the task completes
  before returning the response


*/

/**

download:
    <a href="url" download></a>
    <a href="url" download="filename"></a>
*/

from module daedalus import {
    StyleSheet,
    DomElement,
    TextElement,
    ButtonElement,
    TextInputElement,
    LinkElement,
    Router
}
import module api
import module router
import module resources
import module components
import module store

/*
const encryptionColorMap = {
    system: "#9b111e",
    server: "#0f52ba",
    client: "#FFD700",
    none: "#000000",
}
*/
const thumbnailFormats = {
    jpg: true,
    png: true,
    webm: true,
    mp4: true,
    gif: true,
}

const style = {
    item_file: StyleSheet({color: "blue", cursor: 'pointer'}),

    list: StyleSheet({display: 'flex', 'flex-direction': 'column'}),
    listItem: StyleSheet({
        padding-top: '.25em',
        padding-bottom: '.25em',
        padding-right: '1em',
        padding-left: '1em',
        display: 'flex',
        'border-bottom': {width: '1px', color: '#000000', 'style': 'solid'},
        'flex-direction': 'column',
        'justify-content': 'flex-start',
        'align-items': 'flex-begin',
    }),
    listItemMain: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%'
    }),
    listItemDir: StyleSheet({
        padding-top: '.25em',
        padding-bottom: '.25em',
        padding-right: '1em',
        padding-left: '1em',
        'border-bottom': {width: '1px', color: '#000000', 'style': 'solid'},
        display: 'flex',
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        //width: '100%'
    }),
    listItemMid: StyleSheet({
        'flex-grow': '1',
    }),
    listItemEnd: StyleSheet({
        'margin-left': '1em',
        'margin-right': '1em',
        'cursor': 'pointer'
    }),
    listItemText: StyleSheet({}),
    icon1: StyleSheet({
        'margin-right': '1em'
    }),
    icon2: StyleSheet({
        'margin-right': '1em',
        //border: {width: '1px', color: '#000000', 'style': 'solid'}
    }),
    fileDetailsShow: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'justify-content': 'flex-start',
        'align-items': 'flex-begin',
    }),
    fileDetailsHide: StyleSheet({display: 'none'}),


    encryption: {
        "system": StyleSheet({'min-width': '1em', width: '1em', 'border-color': '#000000', 'border-width': '1px', 'border-radius': '5px 0 0 5px', height: '62px', background: "#9b111e"}),
        "server": StyleSheet({'min-width': '1em', width: '1em', 'border-color': '#000000', 'border-width': '1px', 'border-radius': '5px 0 0 5px', height: '62px', background: "#0f52ba"}),
        "client": StyleSheet({'min-width': '1em', width: '1em', 'border-color': '#000000', 'border-width': '1px', 'border-radius': '5px 0 0 5px', height: '62px', background: "#FFD700"}),
        "none":   StyleSheet({'min-width': '1em', width: '1em', 'border-color': '#000000', 'border-width': '1px', 'border-radius': '5px 0 0 5px', height: '62px', background: "#000000"}),
    },

    svgDiv: StyleSheet({
        'min-width': '82px',
        'min-height': '62px',
        'width': '82px',
        'height': '62px',
        'margin-right':  '0.5em'
    }),

    text: StyleSheet({
        width: '100%',
        'text-overflow': 'ellipsis',
        'white-space':'nowrap',
    }),
    textSpacer: StyleSheet({
        'margin-left': '0em',
        'margin-right': '1em'
    }),

    callbackLink: StyleSheet({
        cursor: 'pointer', color: 'blue'
    }),
    center: StyleSheet({
        'text-align': 'center',
        //'position': 'sticky',
        'background': '#238e23',
        'padding-left': '2em',
        top:0
    }),
    paddedText: StyleSheet({
        'padding-top': '.5em',
        'padding-bottom': '.5em',
    }),
    navBar: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%'
    }),
    searchShow: StyleSheet({display: 'block'}),
    searchHide: StyleSheet({display: 'none'}),
    grow: StyleSheet({
        'flex-grow': 1,
    }),
    objectContainer: StyleSheet({
        'height': '96vh',
        'padding-top': '2vh',
        'width': '90%',
        'padding-left': '5%',
    }),
    zoomOut: StyleSheet({
        cursor: "zoom-out",
    }),
    zoomIn: StyleSheet({
        cursor: "zoom-in",
        display: "flex",
        justify-content: "center",
        align-items: 'center',
        height: "100vh"
    }),
    maxWidth: StyleSheet({
        max-width: "100%",
        max-height: "100%",
    }),
    main2: StyleSheet({
        display: 'inline-flex',
        'flex-direction': 'column',
        'justify-content': 'center',
        'margin-top': '25vh',
        'margin-left': '25%',
        width: '50%',
        'min-width': '9em',
        height: '50vh',
        'min-height': '6em',
        'background-image': 'linear-gradient(#08B214, #078C12)',
        'border': "solid 1px transparent",
        'border-radius': '1em',
        'text-align': 'center',
        'box-shadow': '5px 5px 5px 5px rgba(0,0,0,.6)'
    }),
    show: StyleSheet({}),
    hide: StyleSheet({display: "none"})
}

StyleSheet(`.${style.listItem}:hover`, {background: '#0000FF22'})
StyleSheet(`.${style.listItemDir}:hover`, {background: '#0000FF22'})


/*
the thumbnail_work_queue, combined with the functions
thumbnail_DoProcessNext, thumbnail_ProcessNext, thumbnail_CancelQueue
and classes SvgIconElementImpl, SvgIconElement work together
to implement a way to lazy load thumbnails. Only one request to the
backend is made at a time.

when constructing instance of SvgIconElementImpl populate the queue
The User must then manually start the process by calling thumbnail_ProcessNext
Each time a thumbnail successfully or fails to load the next thumbnail
will start loading.
*/
let thumbnail_work_queue = []
// the number of active 'threads' performing work
let thumbnail_work_count = 0

function thumbnail_DoProcessNext() {

    if (thumbnail_work_queue.length > 0) {
        const elem = thumbnail_work_queue.shift()
        if (elem.props.src != elem.state.url1) {
            elem.updateProps({src: elem.state.url1})
        } else {
            thumbnail_ProcessNext()
        }
    }
}

function thumbnail_ProcessNext() {

    if (thumbnail_work_queue.length > 0) {
        requestIdleCallback(thumbnail_DoProcessNext)
    } else {
        thumbnail_work_count -= 1
    }
}

function thumbnail_ProcessStart() {

    // run the work queue with two chains in parallel
    if (thumbnail_work_queue.length >= 3) {
        requestIdleCallback(thumbnail_DoProcessNext)
        requestIdleCallback(thumbnail_DoProcessNext)
        requestIdleCallback(thumbnail_DoProcessNext)
        thumbnail_work_count = 3
    } else if (thumbnail_work_queue.length > 0) {
        requestIdleCallback(thumbnail_DoProcessNext)
        thumbnail_work_count = 1
    }
}

function thumbnail_CancelQueue() {
    thumbnail_work_queue = []
    thumbnail_work_count = 0
}

class SvgIconElementImpl extends DomElement {
    constructor(url1, url2, props) {
        super("img", {src:url2, width: 80, height: 60, ...props}, [])

        this.state = {
            url1, url2
        }

        if (url1 !== url2 && url1 && url2) {
            thumbnail_work_queue.push(this)
        }
    }

    onLoad(event) {
        // the backup image doesn't effect the work queue
        if (this.props.src === this.state.url2) {
            return
        }

        thumbnail_ProcessNext()
    }

    onError(error) {
        console.warn("error loading: ", this.props.src, JSON.stringify(error))

        if (this.props.src === this.state.url2) {
            return
        }

        if (this.props.src != this.state.url2 && this.state.url2) {
            this.updateProps({src: this.state.url2})
        }

        thumbnail_ProcessNext()
    }
}

class SvgIconElement extends DomElement {
    constructor(url1, url2, props) {
        if (url2 === null) {
            url2 = url1;
        }
        super("div", {className: style.svgDiv}, [new SvgIconElementImpl(url1, url2, props)])
    }
}

class SvgMoreElement extends components.SvgElement {
    constructor(callback) {

        super(resources.svg.more, {width: 20, height: 60, className: style.listItemEnd})

        this.state = {
            callback
        }

    }

    onClick(event) {
        this.state.callback()
    }
}

class StorageListElement extends DomElement {
    constructor(elem) {
        super("div", {className: style.list}, [])
    }
}

class CallbackLink extends DomElement {
    constructor(text, callback) {
        super('div', {className: style.callbackLink}, [new TextElement(text)])

        this.state = {
            callback
        }
    }

    setText(text) {
        this.children[0].setText(text)
    }

    onClick() {
        this.state.callback()
    }
}

class DirectoryElement extends DomElement {
    constructor(name, url) {
        super("div", {className: style.listItemDir}, [])

        this.appendChild(new DomElement("div", {className: style.encryption["none"]}, []))
        this.appendChild(new SvgIconElement(resources.svg.folder, null, {className: style.icon1}))
        this.appendChild(new components.MiddleTextLink(name, url))
        this.children[2].addClassName(style.listItemMid)
    }
}

class DownloadLink extends DomElement {
    // android (chrome) compatible download link
    // the prop 'download' is required inside a webview
    constructor(url, filename) {
        super("a", {href: url, download:filename}, [new TextElement("Download")])
    }
}

class FileElement extends DomElement {
    constructor(fileInfo, callback, delete_callback) {
        super("div", {className: style.listItem}, [])

        this.state = {
            fileInfo,
        }
        this.attrs = {
            main: this.appendChild(new DomElement("div", {className: style.listItemMain}, [])),
            details: null,
            delete_callback,
        }

        const elem = new components.MiddleText(fileInfo.name);
        elem.addClassName(style.listItemMid)
        elem.updateProps({onClick: this.handleShowDetails.bind(this)})
        //const elem = new DomElement("div",
        //    {className: style.text, onClick: this.handleShowDetails.bind(this)},
        //    [new TextElement(fileInfo.name)])

        let url1 = resources.svg.file;
        let url2 = null;
        let className = style.icon1

        const ext = daedalus.util.splitext(fileInfo.name)[1].substring(1).toLocaleLowerCase()
        if (thumbnailFormats[ext]===true) {
            url2 = url1
            url1 = api.fsPathPreviewUrl(fileInfo.root, daedalus.util.joinpath(fileInfo.path, fileInfo.name))
            className = style.icon2
        }

        //this.appendChild(new SvgElement('/static/icon/folder.svg',{width: 80, height: 60}))
        const encryption = fileInfo.encryption || "none"
        this.attrs.main.appendChild(new DomElement("div", {className: style.encryption[encryption]}, []))
        this.attrs.main.appendChild(new SvgIconElement(url1, url2, {className: className}))
        this.attrs.main.appendChild(elem)
        if (callback !== null) {
            this.attrs.main.appendChild(new SvgMoreElement(callback))
        }
    }

    handleShowDetails(event) {
        if (this.attrs.details === null) {
            const fpath = daedalus.util.joinpath(this.state.fileInfo.path, this.state.fileInfo.name)
            this.attrs.details = new DomElement("div", {className: style.fileDetailsShow}, [])
            this.appendChild(this.attrs.details)
            //this.attrs.details.appendChild(new DomElement('div', {className: style.paddedText}, [new LinkElement("Preview",
            //    api.fsPathUrl(this.state.fileInfo.root, fpath, 0))]))
            this.attrs.details.appendChild(new DomElement('div', {className: style.paddedText}, [new LinkElement("Preview",
                api.fsGetPathContentUrl(this.state.fileInfo.root, fpath))]))

            // Old download impl
            //this.attrs.details.appendChild(new DomElement('div', {className: style.paddedText}, [new LinkElement("Download",
            //    api.fsPathUrl(this.state.fileInfo.root, fpath, 1))]))

            // Android compatible download impl
            const dl = new DownloadLink(api.fsPathUrl(this.state.fileInfo.root, fpath, 1), this.state.fileInfo.name);
            this.attrs.details.appendChild(new DomElement('div', {className: style.paddedText}, [dl]))

            this.attrs.details.appendChild(new DomElement('div', {className: style.paddedText}, [new CallbackLink("Delete",
                this.attrs.delete_callback)]))

            if (this.state.fileInfo.encryption == "system") {

                this.attrs.public_container = new DomElement('div', {className: style.paddedText}, []);
                this.attrs.public_link1 = new CallbackLink("Generate Public Link", this.handlePublic1Clicked.bind(this))
                this.attrs.public_link2 = new CallbackLink("Open Public Download Page", this.handlePublic2Clicked.bind(this))
                this.attrs.public_container.appendChild(this.attrs.public_link1)
                this.attrs.public_container.appendChild(this.attrs.public_link2)
                this.attrs.details.appendChild(this.attrs.public_container)
                this._updatePublicLinkText()
            }

            this.attrs.details.appendChild(new DomElement('div', {}, [new TextElement(`Version: ${this.state.fileInfo.version}`)]))
            this.attrs.details.appendChild(new DomElement('div', {}, [new TextElement(`Size: ${this.state.fileInfo.size}`)]))
            this.attrs.details.appendChild(new DomElement('div', {}, [new TextElement(`Encryption: ${this.state.fileInfo.encryption}`)]))
            //this.attrs.details.appendChild(new DomElement('div', {}, [new TextElement(`Public: ${this.state.fileInfo.public}`)]))
            const dt = new Date(this.state.fileInfo.mtime * 1000)
            this.attrs.details.appendChild(new DomElement('div', {}, [new TextElement(`Modified Time: ${dt}`)]))
        } else {
            if (this.attrs.details.props.className === style.fileDetailsShow) {
                this.attrs.details.updateProps({className: style.fileDetailsHide})

            } else {
                this.attrs.details.updateProps({className: style.fileDetailsShow})
            }
        }
    }

    handlePublic1Clicked() {
        console.log("click")
        console.log(this.state.fileInfo)


        const root = this.state.fileInfo.root
        const name = this.state.fileInfo.path + "/" + this.state.fileInfo.name
        if (this.state.fileInfo.public) {
            api.fsPublicUriRevoke(root, name)
                .then(result => {
                    this.state.fileInfo.public = null;
                    this._updatePublicLinkText()
                })
                .catch(error => {console.error(error)})
        } else {
            api.fsPublicUriGenerate(root, name)
                .then(result => {
                    console.log("***", result)
                    this.state.fileInfo.public = result.result['id'];
                    this._updatePublicLinkText()
                })
                .catch(error => {console.error(error)})
        }


    }

    handlePublic2Clicked() {
        console.log("click")
        console.log(this.state.fileInfo)

        const uid = this.state.fileInfo.public;
        const filename = this.state.fileInfo.name;
        let url = location.origin + router.routes.publicFile({uid, filename})
        window.open(url, '_blank');
    }

    _updatePublicLinkText() {

        console.log(this.state.fileInfo.public)

        let text = this.state.fileInfo.public ? "Revoke Public Link" : "Generate Public Link"
        this.attrs.public_link1.setText(text)


        if (this.state.fileInfo.public) {
            this.attrs.public_link2.removeClassName(style.hide)
            this.attrs.public_link2.addClassName(style.show)

        } else {
            this.attrs.public_link2.removeClassName(style.show)
            this.attrs.public_link2.addClassName(style.hide)

        }
    }
}

class StorageNavBar extends DomElement {
    constructor() {
        super("div", {className: style.navBar}, []);
    }

    addActionElement(element) {
        this.appendChild(element)
    }
}

class Header extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        this.addAction(resources.svg['menu'], ()=>{store.globals.showMenu()});
        this.addAction(resources.svg['return'], parent.handleOpenParent.bind(parent));
        this.addAction(resources.svg['upload'], this.handleUploadFile.bind(this));
        this.addAction(resources.svg['search_generic'], parent.handleToggleSearch.bind(parent));
        this.addAction(resources.svg['new_folder'], parent.handleNewDirectory.bind(parent));

        this.attrs.location = new components.MiddleText(".....")
        this.addRow(true)
        this.addRowElement(0, this.attrs.location);

        this.attrs.search_input = new TextInputElement("", null, parent.search.bind(parent));
        this.addRow(false)
        this.attrs.search_input.addClassName(style.grow)
        this.addRowElement(1, this.attrs.search_input);

        this.addRowAction(1, resources.svg['search_generic'], ()=>{});

        this.attrs.uploadManager = new StorageUploadManager(parent.handleInsertUploadFile.bind(parent));
        this.addRow(true)
        this.addRowElement(2, this.attrs.uploadManager);

    }

    setLocation(path) {
        this.attrs.location.setText(path)
    }

    setSearchText(text) {
        this.attrs.search_input.setText(text)
    }

    handleUploadFile() {
        if (this.attrs.parent.state.match.root !== "") {

            this.attrs.uploadManager.startUpload(
                this.attrs.parent.state.match.root,
                this.attrs.parent.state.match.dirpath)

        }
    }

}

class StorageUploadManager extends StorageListElement {
    constructor(insert_callback) {
        super();

        this.attrs = {
            files: {},
            root: null,
            dirpath: null,
            insert_callback
        }

    }

    startUpload(root, dirpath) {

        api.fsUploadFile(
            root,
            dirpath,
            {},
            {crypt: 'system'},
            this.handleUploadFileSuccess.bind(this),
            this.handleUploadFileFailure.bind(this),
            this.handleUploadFileProgress.bind(this))

        this.attrs.root = root
        this.attrs.dirpath = dirpath
    }

    handleUploadFileSuccess(msg) {
        const item = this.attrs.files[msg.fileName]
        item.fileInfo.mtime = msg.lastModified
        this.attrs.insert_callback(item.fileInfo)

        setTimeout(()=>this.handleRemove(msg), 1000)

    }

    handleUploadFileFailure(msg) {
        console.error(msg)
        setTimeout(()=>this.handleRemove(msg), 3000)
    }

    handleUploadFileProgress(msg) {
        if (msg.first) {
            const fileInfo = {
                encryption: 'system',
                mtime: 0,
                name: msg.fileName,
                path: this.attrs.root,
                permission: 0,
                public: "",
                root: this.attrs.dirpath,
                size: msg.fileSize,
                version: 1,
                bytesTransfered: msg.bytesTransfered
            }
            const node = new TextElement(msg.fileName)
            this.attrs.files[msg.fileName] = {fileInfo, node}
            this.appendChild(node)
        } else if (msg.finished) {
            const item = this.attrs.files[msg.fileName]
            if (msg.bytesTransfered == msg.fileSize) {
                item.node.setText(`${msg.fileName}: upload success`)
            } else {
                item.node.setText(`${msg.fileName}: upload failed`)
            }
        } else {
            const item = this.attrs.files[msg.fileName]
            item.fileInfo.bytesTransfered = msg.bytesTransfered
            item.node.setText(`${msg.fileName} ${(100.0*msg.bytesTransfered/msg.fileSize).toFixed(2)}%`)
        }
    }

    handleRemove(msg) {
        const item = this.attrs.files[msg.fileName]

        this.removeChild(item.node);
        delete this.attrs.files[msg.fileName];
    }
}

export class StoragePage extends DomElement {
    constructor() {
        super("div", {}, []);

        this.attrs = {
            header: new Header(this),
            regex: daedalus.patternToRegexp(":root?/:dirpath*", false),
            lst: new StorageListElement(),
            more: new components.MoreMenu(this.handleHideFileMore.bind(this)),
            filemap: {},
        }

        this.state = {
            parent_url: null,
        }

        this.appendChild(this.attrs.more)
        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.lst)


    }

    elementMounted() {
        const params = daedalus.util.parseParameters()
        this.attrs.header.setSearchText((params.q && params.q[0]) || "")
    }

    elementUpdateState(oldState, newState) {
        // when the route changes and assigns a new path to this instance
        // update the incoming match result with the result of the sub path
        // matching
        // note that the top level route could be instead: /u/storage/:root?/:dirpath*
        // this was written only to abuse the element api
        if (newState.match) {
            if (!oldState.match || oldState.match.path !== newState.match.path) {
                const match = daedalus.locationMatch(this.attrs.regex, newState.match.path)
                Object.assign(newState.match, match)

                this.handleRouteChange(newState.match.root, newState.match.dirpath)
            }
        } else {
            newState.match = {root: "", dirpath: ""}
        }

        //if (oldState.parent_url != newState.parent_url) {
        //}
    }

    getRoots() {
        thumbnail_CancelQueue();
        this.attrs.lst.removeChildren();
        api.fsGetRoots()
            .then(data => {this.handleGetRoots(data.result)})
            .catch(error => {this.handleGetRootsError(error)})
    }

    handleGetRoots(result) {
        console.log(result)
        this.updateState({parent_url:null})

        result.forEach(name => {
            let url = '/u/storage/list/' + this.state.match.path + '/' + name
            url = url.replace(/\/\//, '/')
            this.attrs.lst.appendChild(new DirectoryElement(name, url))

        })
    }

    handleGetRootsError(error) {
        console.error(error)
        this.updateState({parent_url:null})
        this.attrs.lst.appendChild(new TextElement("error loading roots"))
    }

    refresh() {
        this.getPath(this.state.match.root, this.state.match.dirpath)
    }

    getPath(root, dirpath) {
        thumbnail_CancelQueue();
        this.attrs.lst.removeChildren();
        api.fsGetPath(root, dirpath)
            .then(data => {this.handleGetPath(data.result)})
            .catch(error => {this.handleGetPathError(error)})
    }

    handleGetPath(result) {

        if (result === undefined) {
            this.attrs.lst.appendChild(new TextElement("Empty Directory (error)"))
            return
        }

        let url;
        if (result.parent === result.path) {
            url = daedalus.util.joinpath('/u/storage/list/')
        } else {
            url = daedalus.util.joinpath('/u/storage/list/', result.name, result.parent)
        }

        this.updateState({parent_url:url})

        const filemap = {};

        if ((result.files.length + result.directories.length) === 0) {

            this.attrs.lst.appendChild(new TextElement("Empty Directory"))

        } else {
            result.directories.forEach(name => {
                let url = daedalus.util.joinpath('/u/storage/list/', this.state.match.path, name)
                this.attrs.lst.appendChild(new DirectoryElement(name, url))
            })

            result.files.forEach(item => {
                //let url = daedalus.util.joinpath('/u/storage/list/', this.state.match.path, item.name)
                const cbk = ()=>{this.handleShowFileMore(item)};
                item.root = this.state.match.root;
                item.path = this.state.match.dirpath;
                const elem = new FileElement(item, cbk, this.deleteElement.bind(this))
                this.attrs.lst.appendChild(elem)
                filemap[item.name] = elem

            })
        }

        // the best order to process elements in would be from first to last
        // the current implementation uses pop (last to first)
        // shuffle the elements to help discover  bugs in the implementation
        //daedalus.util.shuffle(thumbnail_work_queue)
        thumbnail_ProcessStart();

        this.attrs.filemap = filemap;
    }

    handleGetPathError(error) {
        let url = '/u/storage/list/'
        console.log(error)
        if (this.state.match && this.state.match.dirpath) {
            const parts = daedalus.util.splitpath(this.state.match.dirpath)
            parts.pop()
            url =  daedalus.util.joinpath(url, this.state.match.root, ...parts)
        }
        this.updateState({parent_url:url})


        this.attrs.lst.appendChild(new TextElement("Empty Directory (error)"))
    }

    handleToggleSearch() {

        if (this.state.match.root === "") {
            return
        }

        if (this.attrs.search_input.props.className[0] == style.searchHide) {
            this.attrs.search_input.updateProps({className: [style.searchShow]})
            //this.attrs.btnSearch.setText("Cancel")

            //this.attrs.btnBack.addClassName(style.searchHide)
            //this.attrs.btnUpload.addClassName(style.searchHide)
            //this.attrs.btnNewDirectory.addClassName(style.searchHide)

            //this.attrs.btnBack.removeClassName(style.searchShow)
            //this.attrs.btnUpload.removeClassName(style.searchShow)
            //this.attrs.btnNewDirectory.removeClassName(style.searchShow)

            thumbnail_CancelQueue();
            this.attrs.lst.removeChildren();
        } else {
            //this.attrs.btnSearch.setText("Search")
            this.attrs.search_input.updateProps({className: [style.searchHide]})

            //this.attrs.btnBack.addClassName(style.searchShow)
            //this.attrs.btnUpload.addClassName(style.searchShow)
            //this.attrs.btnNewDirectory.addClassName(style.searchShow)

            //this.attrs.btnBack.removeClassName(style.searchHide)
            //this.attrs.btnUpload.removeClassName(style.searchHide)
            //this.attrs.btnNewDirectory.removeClassName(style.searchHide)

            // TODO: this can be optimized in the future by caching the result
            this.refresh()
        }
    }

    search(text) {
        console.log(text)

        thumbnail_CancelQueue();
        this.attrs.lst.removeChildren();

        let root = this.state.match.root,
            path = this.state.match.dirpath,
            terms = text,
            page = 0,
            limit = 100;

        api.fsSearch(root, path, terms, page, limit)
            .then(this.handleSearchResult.bind(this))
            .catch(this.handleSearchError.bind(this))
    }

    handleSearchResult(result) {
        const files = result.result.files
        console.log(files)

        const filemap = {}

        if (files.length === 0) {
            this.attrs.lst.appendChild(new TextElement("No Results"))
        } else {
            try {
                files.forEach(item => {
                    //let url = daedalus.util.joinpath('/u/storage/list/', this.state.match.path, item.name)
                    const cbk1 = ()=>{this.handleShowFileMore(item)};
                    const cbk2 = this.deleteElement.bind(this);
                    item.root = this.state.match.root
                    const parts = daedalus.util.splitpath(item.file_path);
                    parts.pop()
                    item.path = parts.join("/");
                    console.log(item)
                    const elem = new FileElement(item, cbk1, cbk2)
                    this.attrs.lst.appendChild(elem)
                    filemap[item.name] = elem

                })
            } catch (e) {
                console.log(e)
            }
        }

        this.attrs.filemap = filemap;

        //daedalus.util.shuffle(thumbnail_work_queue)
        thumbnail_ProcessStart();
    }

    handleSearchError(error) {
        this.attrs.lst.appendChild(new TextElement("No Results"))
    }

    handleOpenParent() {
        if (this.state.parent_url) {
            history.pushState({}, "", this.state.parent_url)
        }
    }

    handleShowFileMore(item) {

        this.attrs.more.show()
    }

    handleHideFileMore() {

        this.attrs.more.hide()
    }

    handleRouteChange(root, dirpath) {

        if (root === "" && dirpath === "") {
            this.getRoots()
        } else if (root !== "") {
            this.getPath(root, dirpath)
        }

        this.attrs.header.setLocation(root + "/" + dirpath)
    }

    handleInsertUploadFile(fileInfo) {

        if (this.attrs.filemap[fileInfo.name] === undefined) {
            const elem = new FileElement(fileInfo, null, this.deleteElement.bind(this))
            this.attrs.lst.insertChild(0, elem)
        } else {
            const elem = filemap[fileInfo.name]
        }
    }

    deleteElement(elem, fileInfo) {
        console.log(fileInfo)
    }

    handleNewDirectory(){
        console.log("mkdir")
    }
}

class FormattedText extends DomElement {
    constructor(text) {
        super("pre", {style:{margin:0}}, [new TextElement(text)]);
    }

    setText(text) {
        this.children[0].setText(text)
    }
}

const preview_formats = {
    '.mp4': 'video',
    '.webm': 'video',

    '.jpg': 'image',
    '.jpeg': 'image',
    '.gif': 'image',
    '.png': 'image',
    '.bmp': 'image',

    '.wav': 'audio',
    '.mp3': 'audio',

    '.pdf': 'pdf',
}

export class StoragePreviewPage extends DomElement {
    constructor() {
        super("div", {}, []);


        this.attrs = {
            regex: daedalus.patternToRegexp(":root?/:dirpath*", false),
        }
        console.log(this.attrs.regex)

    }

    elementUpdateState(oldState, newState) {
        if (newState.match && (!oldState.match || oldState.match.path !== newState.match.path)) {
            const match = daedalus.locationMatch(this.attrs.regex, newState.match.path)
            Object.assign(newState.match, match)
            this.handleRouteChange(newState.match.root, newState.match.dirpath)
        } else {
            if (newState.match) {
                Object.assign(newState.match, {root: "", path: ""})
            } else {
                newState.match = {root: "", path: ""}
            }
        }
    }

    handleRouteChange(root, path) {

        const [_, ext] = daedalus.util.splitext(path.toLocaleLowerCase())

        const format = preview_formats[ext]

        if (format === undefined) {
            api.fsGetPathContent(root, path)
                .then(res=>{this.appendChild(new FormattedText(res))})
                .catch(err=>console.error(err))
        } else if (format === 'image') {
            // TODO: images should be centered, click/tap for full size
            const url = api.fsPathUrl(root, path, 0)
            console.log(url)
            let img = new DomElement("img", {src: url, className: style.maxWidth}, [])
            let div = new DomElement("div", {className: style.zoomIn, onClick: this.toggleImageZoom.bind(this)}, [img])
            this.attrs.img = img
            this.attrs.img_div = div
            this.appendChild(div)
        } else if (format === 'video') {
            // TODO: videos should be centered, click/tap for full size
            const url = api.fsPathUrl(root, path, 0)
            this.appendChild(new DomElement("video", {src: url, controls: 1}, []))
        } else if (format === 'pdf') {
            const url = api.fsPathUrl(root, path, 0)
            console.warn(url)
            this.addClassName(style.objectContainer)
            this.appendChild(new DomElement("object", {
                data: url,
                type: 'application/pdf',
                width: '100%',
                height: '100%',
            }, []))
        }
    }

    toggleImageZoom(event) {
        if (this.attrs.img_div.hasClassName(style.zoomIn)) {
            this.attrs.img_div.removeClassName(style.zoomIn)
            this.attrs.img.removeClassName(style.maxWidth)
            this.attrs.img_div.addClassName(style.zoomOut)
        } else {
            this.attrs.img_div.removeClassName(style.zoomOut)
            this.attrs.img_div.addClassName(style.zoomIn)
            this.attrs.img.addClassName(style.maxWidth)
        }
    }
}

class FileSystemDirectoryElement extends DomElement {
    constructor(parent, name, url) {
        super("div", {className: style.listItemDir}, [])

        this.appendChild(new DomElement("div", {className: style.encryption["none"]}, []))
        this.appendChild(new SvgIconElement(resources.svg.folder, null, {className: style.icon1}))
        this.attrs.text = this.appendChild(new components.MiddleText(name))
        this.attrs.text.props.onClick = this.handleClick.bind(this)
        this.children[2].addClassName(style.listItemMid)
        this.attrs.parent = parent
        this.attrs.url = url
    }

    handleClick() {
        this.attrs.parent.setCurrentPath(this.attrs.url)
    }
}

class FileSystemFileElement extends DomElement {
    constructor(parent, item, url) {
        super("div", {className: style.listItemDir}, [])

        this.appendChild(new DomElement("div", {className: style.encryption["none"]}, []))
        this.appendChild(new SvgIconElement(resources.svg.file, null, {className: style.icon1}))
        this.appendChild(new components.MiddleText(item.name))
        this.children[2].addClassName(style.listItemMid)
        this.attrs.parent = parent
        this.attrs.url = url
    }
}


class FileSystemHeader extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent

        this.addAction(resources.svg['menu'], ()=>{store.globals.showMenu()});
        this.addAction(resources.svg['return'], parent.handleOpenParent.bind(parent));

        this.attrs.location = new components.MiddleText(".....")
        this.addRow(true)
        this.addRowElement(0, this.attrs.location);
    }

    setLocation(location) {
        this.attrs.location.setText(location)
    }

}

export class FileSystemPage extends DomElement {
    constructor() {
        super("div", {}, []);

        this.attrs = {
            header: new FileSystemHeader(this),
            lst: new StorageListElement(),
            current_path: "/",
        }


        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.lst)


    }

    elementMounted() {

        this.setCurrentPath("/")
    }

    handleOpenParent() {
        this.setCurrentPath(daedalus.util.dirname(this.attrs.current_path))
    }

    setCurrentPath(path) {

        if (path.length === 0) {
            path = "/"
        }

        console.log(`navigate to \`${path}\``)

        this.attrs.current_path = path
        this.attrs.lst.removeChildren();
        this.attrs.header.setLocation(path)

        if (daedalus.platform.isAndroid) {

            let result = Client.listDirectory(path)
            result = JSON.parse(result)
            this.updateContents(result)
        } else {
            const result = {
                files: [{name: "file1"}],
                directories: ["dir0", "dir1"],
            }
            this.updateContents(result)
        }

        return
    }

    updateContents(result) {

        if ((result.files.length + result.directories.length) === 0) {

            this.attrs.lst.appendChild(new TextElement("Empty Directory"))

        } else {
            result.directories.forEach(name => {
                let url = daedalus.util.joinpath(this.attrs.current_path, name)
                const elem = new FileSystemDirectoryElement(this, name, url)
                this.attrs.lst.appendChild(elem)
            })

            result.files.forEach(item => {
                let url = daedalus.util.joinpath(this.attrs.current_path, name)
                const elem = new FileSystemFileElement(this, item, url)
                this.attrs.lst.appendChild(elem)
            })
        }

    }
}


export class PublicFilePage extends DomElement {
    constructor() {
        super("div", {className: style.main2}, []);
    }

    elementMounted() {

        const m = this.state.match
        const url = api.fsGetPublicPathUrl(m.uid, m.filename)

        api.fsPublicUriInfo(m.uid, m.filename)
            .then(result => {
                this.appendChild(new DomElement("h2", {}, [new TextElement("Download File")]))
                this.appendChild(new DomElement("a", {href: url, download:m.filename}, [new TextElement(m.filename)]))
                this.appendChild(new components.VSpacer("1em"))
                this.appendChild(new TextElement("File Size: " + Math.floor(result.result.file.size/1024) + "kb"))
            })
            .catch(error => {
                this.appendChild(new DomElement("h2", {}, [new TextElement("File Not Found")]))
            })

    }
}
