
/**
SERVER SIDE TODO:
- limit simultaneous transcodes using the task engine
  each request submits a task and waits until the task completes
  before returning the response
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
const extPreview = {
    jpg: true,
    png: true,
    webm: true,
    mp4: true,
    gif: true,
}

const style = {
    item_hover: StyleSheet({background: '#0000CC22'}),
    item: StyleSheet({}),
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
    listItemEnd: StyleSheet({
        'margin-left': 'auto',
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
        "system": StyleSheet({width: '1em', 'border-color': '#000000', 'border-width': '1px', 'border-radius': '5px 0 0 5px', height: '60px', background: "#9b111e"}),
        "server": StyleSheet({width: '1em', 'border-color': '#000000', 'border-width': '1px', 'border-radius': '5px 0 0 5px', height: '60px', background: "#0f52ba"}),
        "client": StyleSheet({width: '1em', 'border-color': '#000000', 'border-width': '1px', 'border-radius': '5px 0 0 5px', height: '60px', background: "#FFD700"}),
        "none":   StyleSheet({width: '1em', 'border-color': '#000000', 'border-width': '1px', 'border-radius': '5px 0 0 5px', height: '60px', background: "#000000"}),
    }
}

StyleSheet(`.${style.item}:hover`, {background: '#0000FF22'})
StyleSheet(`.${style.listItem}:hover`, {background: '#0000FF22'})

// order of these rules is important, hover before active
StyleSheet(`.${style.moreMenuButton}:hover`, {
    'background-image': 'linear-gradient(#BCBCBC, #5E5E5E)';
})

StyleSheet(`.${style.moreMenuButton}:active`, {
    'background-image': 'linear-gradient(#5E5E5E, #BCBCBC)';
})

class SvgElement extends DomElement {
    constructor(url, props) {
        super("img", {src:url, ...props}, [])
    }
}

class SvgIconElement extends DomElement {
    constructor(url1, url2, props) {
        super("img", {src:url1, width: 80, height: 60, ...props}, [])

        this.state = {
            url1, url2
        }
    }

    onError() {
        console.warn("error loading: ", this.props.src)
        if (this.props.src != this.state.url2 && this.state.url2) {
            this.updateProps({src: this.state.url2})
        }
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

class ListElement extends DomElement {
    constructor(elem) {
        super("div", {className: style.list}, [])
    }
}

class DirectoryElement extends DomElement {
    constructor(name, url) {
        super("div", {className: style.listItemDir}, [])

        this.appendChild(new DomElement("div", {className: style.encryption["none"]}, []))
        this.appendChild(new SvgIconElement('/static/icon/folder.svg', null, {className: style.icon1}))
        this.appendChild(new LinkElement(name, url))
    }
}

class FileElement extends DomElement {
    constructor(fileInfo, callback) {
        super("div", {className: style.listItem}, [])

        this.state = {
            fileInfo,
        }
        this.attrs = {
            main: this.appendChild(new DomElement("div", {className: style.listItemMain}, [])),
            details: null,
        }

        const elem = new DomElement("div", {onClick: this.handleShowDetails.bind(this)}, [new TextElement(fileInfo.name)])

        let url1 = '/static/icon/file.svg';
        let url2 = null;
        let className = style.icon1

        const ext = fileInfo.name.split('.').pop()
        if (extPreview[ext]===true) {
            url2 = url1
            url1 = api.fsPathPreviewUrl(fileInfo.root, fileInfo.path + '/' + fileInfo.name)
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
        console.log(this.state.fileInfo)
        if (this.attrs.details === null) {
            this.attrs.details = new DomElement("div", {className: style.fileDetailsShow}, [])
            this.appendChild(this.attrs.details)
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
        super("div", {className: [style.moreMenuButton]}, [new TextElement(text)])
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

export class StoragePage extends DomElement {
    constructor() {
        super("div", {}, []);

        this.attrs = {
            txt: new TextElement(""),
            regex: daedalus.patternToRegexp(":root?/:dirpath*", false),
            lst: new ListElement(),
            more: new MoreMenuShadow(this.handleHideFileMore.bind(this)),
        }


        this.appendChild(this.attrs.more)
        this.appendChild(this.attrs.txt)

        this.appendChild(this.attrs.lst)

    }

    elementUpdateState(oldState, newState) {
        // when the route changes and assigns a new path to this instance
        // update the incoming match result with the result of the sub path
        // matching
        // note that the top level route could be instead: /u/storage/:root?/:dirpath*
        // this was written only to abuse the element api
        if (newState.match && (!oldState.match || oldState.match.path !== newState.match.path)) {
            const match = daedalus.locationMatch(this.attrs.regex, newState.match.path)
            Object.assign(newState.match, match)
            this.handleRouteChange(newState.match.root, newState.match.dirpath)
        } else {
            if (newState.match) {
                Object.assign(newState.match, {root: "", dirpath: ""})
            } else {
                newState.match = {root: "", dirpath: ""}
            }
        }


    }

    getRoots() {
        api.fsGetRoots()
            .then(data => {this.handleGetRoots(data.result)})
            .catch(error => {console.error(error)})
    }

    handleGetRoots(result) {
        console.log(result)

        this.attrs.lst.removeChildren()

        result.forEach(name => {
            console.log(this.state.match, name)
            let url = '/u/storage/list/' + this.state.match.path + '/' + name
            url = url.replace(/\/\//, '/')
            this.attrs.lst.appendChild(new DirectoryElement(name, url), null)

        })

    }

    getPath(root, dirpath) {
        api.fsGetPath(root, dirpath)
            .then(data => {this.handleGetPath(data.result)})
            .catch(error => {console.error(error)})
    }

    handleGetPath(result) {
        console.log(result)

        this.attrs.lst.removeChildren()

        let url;
        if (result.parent === result.path) {
            url = daedalus.util.joinpath('/u/storage/list/')
        } else {
            url = daedalus.util.joinpath('/u/storage/list/', result.name, result.parent)
        }
        console.log(url)

        this.attrs.lst.appendChild(new DirectoryElement("up one level", url), null)

        result.directories.forEach(name => {
            let url = daedalus.util.joinpath('/u/storage/list/', this.state.match.path, name)
            this.attrs.lst.appendChild(new DirectoryElement(name, url), null)

        })

        result.files.forEach(item => {
            let url = daedalus.util.joinpath('/u/storage/list/', this.state.match.path, item.name)
            const cbk = ()=>{this.handleShowFileMore(item)};
            item.root = this.state.match.root;
            item.path = this.state.match.dirpath;
            this.attrs.lst.appendChild(new FileElement(item, cbk))

        })

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
}