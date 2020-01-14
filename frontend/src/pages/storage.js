
/**
SERVER SIDE TODO:
- limit simultaneous transcodes using the task engine
  each request submits a task and waits until the task completes
  before returning the response

- thumbnail images need a special class to handle concurrency better

  new Thumb()         - enqueue this onto a work queue
  Thumb.cancelWork()  - remove all elements from the work queue
  use the idle request api to start a work look to process the work
  to be done. When opening a new page cancel existing work, creating
  the FileElements will create new Thumb() elements and enqueue the work
  When the Thumb is created, the src prop is not set.
  The work to be done is to set the src prop for a single image and
  on success or failure move on to the next image.

*/
import daedalus with {
    StyleSheet,
    DomElement,
    TextElement,
    ButtonElement,
    TextInputElement,
    LinkElement,
    Router
}
import api
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
        padding: '.25em',
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
        padding: '.25em',
        'border-bottom': {width: '1px', color: '#000000', 'style': 'solid'},
        display: 'flex',
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%'
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
        border: {width: '1px', color: '#000000', 'style': 'solid'}
    }),
    fileDetailsShow: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'justify-content': 'flex-start',
        'align-items': 'flex-begin',
    }),
    fileDetailsHide: StyleSheet({display: 'none'}),
    moreMenuShadow: StyleSheet({
        position: 'fixed',
        top: '0',
        left: '0',
        background: 'rgba(0,0,0,0.33)',
        width: '100vw',
        height: '100vh',
    }),
    moreMenu: StyleSheet({
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        background: 'white',
        width: '50vw',
        'min-width': '10em',
        'min-height': '10em',
        'box-shadow': '.5em .5em .5em 0 rgba(0,0,0,0.50)',
        padding: '1em'
    }),
    moreMenuShow: StyleSheet({display: 'block'}),
    moreMenuHide: StyleSheet({display: 'none'}),

    // light color is chosen,
    // dark color is 50% of light color
    // hover light color is 10% darker,
    // hover dark color is 50% of hover light color
    // border color is HSV half way between both dark colors
    // active color inverts hover
    moreMenuButton: StyleSheet({
        border: {'radius': '.5em', color: '#646464', style: 'solid', width: '1px'},
        padding: '1em',
        'background-image': 'linear-gradient(#D5D5D5, #6A6A6A)',
        'text-align': 'center'
    }),

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
    // http://jsfiddle.net/4ah8ernc/2/
    ellideMiddle: StyleSheet({
        display: 'inline-flex',
        'flex-wrap': 'nowrap',
        'max-width': '100%',
        'min-width': '0',
    }),
    ellideMiddleDiv1: StyleSheet({
        flex: '0 1 auto',
        'text-overflow': 'ellipsis',
        overflow: 'hidden',
        'white-space': 'nowrap',
    }),
    ellideMiddleDiv2: StyleSheet({
        flex: '1 0 auto',
        'white-space': 'nowrap',
    }),
    ellideMiddleLink: StyleSheet({
        cursor: 'pointer', color: 'blue'
    }),
    callbackLink: StyleSheet({
        cursor: 'pointer', color: 'blue'
    }),
    center: StyleSheet({
        'text-align': 'center',
        'position': 'sticky',
        'background': '#238e23',
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
}

StyleSheet(`.${style.listItem}:hover`, {background: '#0000FF22'})
StyleSheet(`.${style.listItemDir}:hover`, {background: '#0000FF22'})

// order of these rules is important, hover before active
StyleSheet(`.${style.moreMenuButton}:hover`, {
    'background-image': 'linear-gradient(#BCBCBC, #5E5E5E)';
})

StyleSheet(`.${style.moreMenuButton}:active`, {
    'background-image': 'linear-gradient(#5E5E5E, #BCBCBC)';
})


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

function thumbnail_DoProcessNext() {

    if (thumbnail_work_queue.length > 0) {
        const elem = thumbnail_work_queue.pop()
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
    }
}
function thumbnail_CancelQueue() {
    thumbnail_work_queue = []
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

    onError() {
        console.warn("error loading: ", this.props.src)

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

class SvgElement extends DomElement {
    constructor(url, props) {
        super("img", {src:url, ...props}, [])
    }
}

class SvgMoreElement extends SvgElement {
    constructor(callback) {
        super('/static/icon/more.svg', {width: 20, height: 60, className: style.listItemEnd})

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

class MiddleText extends DomElement {
    constructor(text) {
        super("div", {className: [style.textSpacer]}, [])

        if (text.length > 4) {
            const idx = text.length - 4;
            const text1 = text.substr(0, idx);
            const text2 = text.substr(idx, 4);

            this.updateProps({className: [style.ellideMiddle, style.textSpacer]});

            this.appendChild(new DomElement("div",
                {className: style.ellideMiddleDiv1},
                [new TextElement(text1)]));

            this.appendChild(new DomElement("div",
                {className: style.ellideMiddleDiv2},
                [new TextElement(text2)]));
        } else {
            this.appendChild(new TextElement(text))
        }

    }

    setText(text) {
        const idx = text.length - 4;
        const text1 = text.substr(0, idx);
        const text2 = text.substr(idx, 4);
        this.children[0].children[0].setText(text1)
        this.children[1].children[0].setText(text2)
    }
}

class MiddleTextLink extends MiddleText {
    constructor(text, url) {
        super(text)

        this.state = {
            url
        }

        this.props.className.push(style.ellideMiddleLink)
    }

    onClick() {
        if (this.state.url.startsWith('http')) {
            window.open(this.state.url, '_blank');
        } else {
            history.pushState({}, "", this.state.url)
        }
    }
}

class CallbackLink extends DomElement {
    constructor(text, callback) {
        super('div', {className: style.callbackLink}, [new TextElement(text)])

        this.state = {
            callback
        }
    }

    onClick() {
        this.state.callback()
    }
}

class DirectoryElement extends DomElement {
    constructor(name, url) {
        super("div", {className: style.listItemDir}, [])

        this.appendChild(new DomElement("div", {className: style.encryption["none"]}, []))
        this.appendChild(new SvgIconElement('/static/icon/folder.svg', null, {className: style.icon1}))
        this.appendChild(new MiddleTextLink(name, url))
        this.children[2].addClassName(style.listItemMid)
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

        const elem = new MiddleText(fileInfo.name);
        elem.addClassName(style.listItemMid)
        elem.updateProps({onClick: this.handleShowDetails.bind(this)})
        //const elem = new DomElement("div",
        //    {className: style.text, onClick: this.handleShowDetails.bind(this)},
        //    [new TextElement(fileInfo.name)])

        let url1 = '/static/icon/file.svg';
        let url2 = null;
        let className = style.icon1

        const ext = daedalus.util.splitext(fileInfo.name)[1].substring(1).toLocaleLowerCase()
        if (thumbnailFormats[ext]===true) {
            url2 = url1
            url1 = api.fsPathPreviewUrl(fileInfo.root, daedalus.util.joinpath(fileInfo.path, fileInfo.name))
            console.log(url1)
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
            this.attrs.details.appendChild(new DomElement('div', {className: style.paddedText}, [new LinkElement("Download",
                api.fsPathUrl(this.state.fileInfo.root, fpath, 1))]))
            this.attrs.details.appendChild(new DomElement('div', {className: style.paddedText}, [new CallbackLink("Delete",
                this.attrs.delete_callback)]))
            this.attrs.details.appendChild(new DomElement('div', {}, [new TextElement(`Version: ${this.state.fileInfo.version}`)]))
            this.attrs.details.appendChild(new DomElement('div', {}, [new TextElement(`Size: ${this.state.fileInfo.size}`)]))
            this.attrs.details.appendChild(new DomElement('div', {}, [new TextElement(`Encryption: ${this.state.fileInfo.encryption}`)]))
            this.attrs.details.appendChild(new DomElement('div', {}, [new TextElement(`Public: ${this.state.fileInfo.public}`)]))
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
}

class MoreMenuShadow extends DomElement {
    constructor(callback_close) {
        super("div", {className: [style.moreMenuShadow, style.moreMenuHide]}, [new MoreMenu()])

        this.attrs = {
            callback_close
        }
    }

    onClick() {
        this.attrs.callback_close()
    }
}

class MoreMenuButton extends DomElement {
    constructor(text, callback) {
        super("div", {className: [style.moreMenuButton], onClick: callback}, [new TextElement(text)])
    }

    setText(text) {
        this.children[0].setText(text)
    }
}

class MoreMenu extends DomElement {
    constructor() {
        super("div", {className: [style.moreMenu]}, [])

        this.appendChild(new MoreMenuButton("hello world"))
    }

    onClick(event) {
        event.stopPropagation();
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
            txt: new MiddleText("....."), // TODO FIXME
            regex: daedalus.patternToRegexp(":root?/:dirpath*", false),
            lst: new StorageListElement(),
            more: new MoreMenuShadow(this.handleHideFileMore.bind(this)),
            banner: new DomElement("div", {className: style.center}, []),
            navBar: new StorageNavBar(),
            uploadManager: new StorageUploadManager(this.handleInsertUploadFile.bind(this)),
            search_input: new TextInputElement("", null, this.search.bind(this)),
            btnLogOut: new MoreMenuButton("LogOut", this.handleLogOut.bind(this)),
            btnBack: new MoreMenuButton("Back", this.handleOpenParent.bind(this)),
            btnUpload: new MoreMenuButton("Upload", this.handleUploadFile.bind(this)),
            btnSearch: new MoreMenuButton("Search", this.handleToggleSearch.bind(this)),
            btnNewDirectory: new MoreMenuButton("New Directory", this.handleNewDirectory.bind(this)),
            filemap: {},
        }

        this.state = {
            parent_url: null,
        }

        this.appendChild(this.attrs.more)
        this.appendChild(this.attrs.banner)

        this.attrs.banner.appendChild(this.attrs.txt)
        this.attrs.banner.appendChild(this.attrs.navBar)
        this.attrs.banner.appendChild(this.attrs.search_input)
        this.attrs.banner.appendChild(this.attrs.uploadManager)

        this.attrs.navBar.addActionElement(this.attrs.btnLogOut)
        this.attrs.navBar.addActionElement(this.attrs.btnBack)
        this.attrs.navBar.addActionElement(this.attrs.btnUpload)
        this.attrs.navBar.addActionElement(this.attrs.btnSearch)
        this.attrs.navBar.addActionElement(this.attrs.btnNewDirectory)

        this.attrs.search_input.updateProps({className: [style.searchHide]})

        this.attrs.btnBack.updateProps({className: [style.moreMenuButton, style.searchShow]})
        this.attrs.btnUpload.updateProps({className: [style.moreMenuButton, style.searchShow]})
        this.attrs.btnSearch.updateProps({className: [style.moreMenuButton, style.searchShow]})
        this.attrs.btnNewDirectory.updateProps({className: [style.moreMenuButton, style.searchShow]})

        this.appendChild(this.attrs.lst)

    }

    elementMounted() {
        const params = daedalus.util.parseParameters()
        this.attrs.search_input.setText((params.q && params.q[0]) || "")
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

    handleLogOut() {

        api.clearUserToken();
        history.pushState({}, "", "/")
    }

    getRoots() {
        thumbnail_CancelQueue();
        this.attrs.lst.removeChildren();
        api.fsGetRoots()
            .then(data => {this.handleGetRoots(data.result)})
            .catch(error => {this.handleGetRootsError(error)})
    }

    handleGetRoots(result) {
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
                this.attrs.lst.appendChild(new DirectoryElement(name, url), null)
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
        daedalus.util.shuffle(thumbnail_work_queue)
        thumbnail_ProcessNext();

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
            this.attrs.btnSearch.setText("Cancel")

            this.attrs.btnBack.updateProps({className: [style.moreMenuButton, style.searchHide]})
            this.attrs.btnUpload.updateProps({className: [style.moreMenuButton, style.searchHide]})
            //this.attrs.btnSearch.updateProps({className: [style.moreMenuButton, style.searchShow]})
            this.attrs.btnNewDirectory.updateProps({className: [style.moreMenuButton, style.searchHide]})

            thumbnail_CancelQueue();
            this.attrs.lst.removeChildren();
        } else {
            this.attrs.btnSearch.setText("Search")
            this.attrs.search_input.updateProps({className: [style.searchHide]})

            this.attrs.btnBack.updateProps({className: [style.moreMenuButton, style.searchShow]})
            this.attrs.btnUpload.updateProps({className: [style.moreMenuButton, style.searchShow]})
            //this.attrs.btnSearch.updateProps({className: [style.moreMenuButton, style.searchShow]})
            this.attrs.btnNewDirectory.updateProps({className: [style.moreMenuButton, style.searchShow]})

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
            limit = 25;

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

        daedalus.util.shuffle(thumbnail_work_queue)
        thumbnail_ProcessNext();
    }

    handleSearchError(error) {
        this.attrs.lst.appendChild(new TextElement("No Results"))
    }

    handleOpenParent() {
        if (this.state.parent_url) {
            history.pushState({}, "", this.state.parent_url)
        }
    }

    handleUploadFile() {
        if (this.state.match.root !== "") {

            this.attrs.uploadManager.startUpload(
                this.state.match.root,
                this.state.match.dirpath)

        }
    }

    handleShowFileMore(item) {

        this.attrs.more.updateProps({className: [style.moreMenuShadow, style.moreMenuShow]})
    }

    handleHideFileMore() {

        this.attrs.more.updateProps({className: [style.moreMenuShadow, style.moreMenuHide]})
    }

    handleRouteChange(root, dirpath) {

        if (root === "" && dirpath === "") {
            this.getRoots()
        } else if (root !== "") {
            this.getPath(root, dirpath)
        }

        this.attrs.txt.setText(root + "/" + dirpath)
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
            this.appendChild(new DomElement("img", {src: url}, []))
        } else if (format === 'video') {
            // TODO: videos should be centered, click/tap for full size
            const url = api.fsPathUrl(root, path, 0)
            this.appendChild(new DomElement("video", {src: url, controls: 1}, []))
        } else if (format === 'pdf') {
            // TODO: videos should be centered, click/tap for full size
            const url = api.fsPathUrl(root, path, 0)
            console.warn(url)
            this.appendChild(new DomElement("object", {
                data: url,
                type: 'application/pdf',
                width: '100%',
                height: '100%',
            }, []))
        }
    }
}
