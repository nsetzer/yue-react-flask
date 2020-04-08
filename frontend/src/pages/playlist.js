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
import module resources
import module audio

const style = {
    main: StyleSheet({
        width: '100%',
    }),

    toolbar: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%',
        'padding-top': '.5em'
    }),

    info: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'justify-content': 'center',
        'align-items': 'center',
        width: '100%'
    }),

    songItem: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'padding-left': '1em',
        'padding-right': '1em',
        'padding-bottom': '.5em',
        //width: '100%',
        border: {style: "solid", width: "1px"}
    }),

    songItemPlaceholder: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'padding-left': '1em',
        'padding-right': '1em',
        'padding-bottom': '.5em',
        border: {style: "solid", width: "1px"},
        background-color: "#edf2f7",
        border: "2px dashed #cbd5e0",
    }),

    songItemActive: StyleSheet({
        background: '#00FF0022',
    }),

    fontBig: StyleSheet({
        'font-size': "120%"
    }),

    fontSmall: StyleSheet({
        'font-size': "80%"
    }),

    songItemRow: StyleSheet({
        display:'flex',
        'flex-direction': 'row'
    }),
    songItemRow2: StyleSheet({
        display: 'flex',
        'justify-content': 'space-between',
        'padding-left': '1em',
        //'padding-right': '1em',
        'align-items': 'baseline'
    }),

    callbackLink2: StyleSheet({
        cursor: 'pointer',
        color: 'blue',
        'padding-right': '1em'
    }),

    grip: StyleSheet({
        cursor: "ns-resize",
        width: "2em",
        min-width: "2em",
        height: "2em",
        background: "linear-gradient(rgba(0,0,0,0) 30%, rgba(0,0,0,.3) 40%, rgba(0,0,0,0) 50%, rgba(0,0,0,.3) 60%, rgba(0,0,0,0) 70%);",
    }),
    space5 : StyleSheet({width: ".5em", min-width: ".5em"})
}


StyleSheet(`.${style.songItem}:hover`, {background: '#0000FF22'})


function formatTime(secs) {
    secs = secs===Infinity?0:secs
    let minutes = Math.floor(secs / 60) || 0;
    let seconds = Math.floor(secs - minutes * 60) || 0;
    return minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
}


class CallbackLink2 extends DomElement {
    constructor(text, callback) {
        super('div', {className: style.callbackLink2}, [new TextElement(text)])

        this.state = {
            callback
        }
    }

    onClick() {
        this.state.callback()
    }
}

class SongItem extends DomElement {
    constructor(parent, index, song) {
        super("div", {className: style.songItem}, []);

        this.attrs = {
            parent,
            index,
            song,
            active: false,
            toolbar: new DomElement("div", {className:style.toolbar}, [])
        }

        const div2 = this.appendChild(new DomElement("div", {className: style.songItemRow}, []))

        div2.appendChild(new DomElement("div", {className:style.space5}, []) )
        const grip = div2.appendChild(new DomElement("div", {className:style.grip}, []) )
        div2.appendChild(new DomElement("div", {className:style.space5}, []) )

        grip.props.onMouseDown = (event) => {
            this.attrs.parent.handleChildDragBegin(this, event)
            let node = this.getDomNode()
            node.style.left = '0px'
            node.style.right = '0px'
            node.style.background = "white"
            event.stopPropagation()
        }

        grip.props.onTouchStart = (event) => {
            this.attrs.parent.handleChildDragBegin(this, event)
            let node = this.getDomNode()
            node.style.left = '0px'
            node.style.right = '0px'
            node.style.background = "white"
            event.stopPropagation()
        }

        const divrhs = div2.appendChild(new DomElement("div", {className:style.main}, []))

        this.attrs.txt1 = divrhs.appendChild(new components.MiddleText((index+1) + ". " + song.title))
        this.attrs.txt1.addClassName(style.fontBig)
        const div = divrhs.appendChild(new DomElement("div", {}, []))

        this.attrs.txt2 = div.appendChild(new components.MiddleText(song.artist))
        //this.attrs.txt2.addClassName(style.fontSmall)
        this.attrs.txt3 = div.appendChild(new TextElement(formatTime(song.length))
        div.addClassName(style.fontSmall)
        div.addClassName(style.songItemRow2)

        this.attrs.toolbar.appendChild(new CallbackLink2("play", ()=>{
            audio.AudioDevice.instance().playIndex(this.attrs.index)
        }))
        this.attrs.toolbar.appendChild(new CallbackLink2("move up", ()=>{
            audio.AudioDevice.instance().queueMoveSongUp(this.attrs.index)
        }))
        this.attrs.toolbar.appendChild(new CallbackLink2("move down", ()=>{
            audio.AudioDevice.instance().queueMoveSongDown(this.attrs.index)
        }))
        this.attrs.toolbar.appendChild(new CallbackLink2("delete", ()=>{
            audio.AudioDevice.instance().queueRemoveIndex(this.attrs.index)
        }))


        divrhs.appendChild(this.attrs.toolbar)

    }

    updateActive(id) {
        if (id === undefined) {
            console.error("err undef")
            return;
        }
        const active = id === this.attrs.song.id
        if (this.attrs.active != active) {
            this.attrs.active = active
            if (active === true) {
                this.attrs.txt1.setText((this.attrs.index+1) + ". *** " + this.attrs.song.title)
                this.addClassName(style.songItemActive)
            } else {
                this.removeClassName(style.songItemActive)
                this.attrs.txt1.setText((this.attrs.index+1) + ". " + this.attrs.song.title)
            }
        }
    }

    onTouchMove(event) {
        this.attrs.parent.handleChildDragMove(this, event)
        event.stopPropagation()
    }

    onTouchEnd(event) {
        this.attrs.parent.handleChildDragEnd(this, {target: this.getDomNode()})
        let node = this.getDomNode()
        node.style.removeProperty('left');
        node.style.removeProperty('right');
        node.style.removeProperty('background');
        event.stopPropagation()
    }

    onTouchCancel(event) {
        this.attrs.parent.handleChildDragEnd(this, {target: this.getDomNode()})
        event.stopPropagation()
    }

    onMouseMove(event) {
        this.attrs.parent.handleChildDragMove(this, event)
        event.stopPropagation()
    }

    //onMouseLeave(event) {
    //    this.attrs.parent.handleChildDragEnd(this, event)
    //    event.stopPropagation()
    //}

    onMouseUp(event) {
        this.attrs.parent.handleChildDragEnd(this, event)
        let node = this.getDomNode()
        node.style.removeProperty('left');
        node.style.removeProperty('right');
        node.style.removeProperty('background');
        event.stopPropagation()
    }

}

class Header extends components.NavHeader {
    constructor(parent) {
        super();

        this.attrs.parent = parent

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
        this.addAction(resources.svg['media_next'], ()=>{
            let inst = audio.AudioDevice.instance()
            inst.setCurrentTime(inst.duration() - 3)
        })
        /*
        this.addAction(resources.svg['media_shuffle'], ()=>{
            audio.AudioDevice.instance().queueCreate(this.attrs.txtInput.props.value)
        }))

        this.addAction(resources.svg['media_shuffle'], ()=>{
            audio.AudioDevice.instance().queueCreate("genre = stoner")
        }))

        this.addAction(resources.svg['media_shuffle'], ()=>{
            audio.AudioDevice.instance().queueCreate('("visual kei" || genre=j-metal ||(genre =j-rock && genre = "nu metal")) && rating > 0')
        }))
        */
        this.addAction(resources.svg['save'], ()=>{
            audio.AudioDevice.instance().queueSave()
        })

        this.attrs.txt_SongTitle = new components.MiddleText("Select A Song")
        this.attrs.txt_SongTime = new TextElement("00:00:00/00:00:00")

        this.addRow(true)
        this.addRow(true)

        this.addRowElement(0, this.attrs.txt_SongTitle)
        this.addRowElement(1, this.attrs.txt_SongTime)

        this.attrs.txt_SongTime.props.onClick = () => {
            const device = audio.AudioDevice.instance();
            device.setCurrentTime(device.duration() - 2)
        }
    }

    setSong(song) {
        if (song === null) {
            this.attrs.txt_SongTitle.setText("Select A Song")
        } else {
            this.attrs.txt_SongTitle.setText(song.artist + " - " + song.title)
        }
    }

    setTime(currentTime, duration) {

        try {
            // todo I think this can be optimized for cases where the
            // text does not change
            const t1 = formatTime(currentTime)
            const t2 = formatTime(duration)
            this.attrs.txt_SongTime.setText(t1 + "/" + t2)
        } catch (e) {
            console.error(e)
        }
    }
}

class SongList extends daedalus.DraggableList {

    updateModel(indexStart, indexEnd) {
        super.updateModel(indexStart, indexEnd);

        audio.AudioDevice.instance().queueSwapSong(indexStart, indexEnd)
    }

}

export class PlaylistPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            device: audio.AudioDevice.instance(),
            header: new Header(this),
            container: new SongList()
        }

        this.attrs.container.setPlaceholderClassName(style.songItemPlaceholder)

        this.appendChild(this.attrs.header)
        //this.appendChild(new TextElement("Loading..."))
        this.appendChild(this.attrs.container)

    }

    elementMounted() {
        console.log("mount playlist view")

        this.attrs.device.connectView(this)

        if (this.attrs.device.queueLength()==0) {
            this.attrs.device.queueLoad()
        } else {
            console.log("update")
            this.handleAudioQueueChanged(this.attrs.device.queue)
            this.handleAudioSongChanged(this.attrs.device.current_song)
        }


    }

    elementUnmounted() {
        console.log("dismount playlist view")

        this.attrs.device.disconnectView(this)
    }

    handleAudioPlay(event) {
        console.log("on play")
    }

    handleAudioPause(event) {
        console.log("on pause")
    }

    handleAudioTimeUpdate(event) {
        this.attrs.header.setTime(event.currentTime, event.duration)
    }

    handleAudioDurationChange(event) {
        this.attrs.header.setTime(event.currentTime, event.duration)
    }

    handleAudioSongChanged(song) {
        this.attrs.header.setSong(song)

        // TODO: if the song changes should that also trigger
        // a reset of time and duration? should that be done in
        // the audio player or in a audio client?

        if (song !== null && song.id) {
            this.attrs.container.children.forEach(child => {
                child.updateActive(song.id)
            })

            this.attrs.header.setTime(0, 0)
        } else {
            console.error("song error", song)
        }
    }

    handleAudioQueueChanged(songList) {

        // TODO: better algorithm
        //  first scan through all existing children
        //  and replace items where the song id does not match
        //  then either remove additional items greater than
        //  the length of the new list or append items from the
        //  new list

        //this.attrs.container.removeChildren()

        const current_id = audio.AudioDevice.instance().currentSongId();

        let miss = 0;
        let hit = 0;
        let index = 0;
        let item = null;
        // get the shorter of the two lists
        const containerList = this.attrs.container.children;
        const N = containerList.length < songList.length ? containerList.length : songList.length

        // update in place
        for (; index < containerList.length && index < songList.length; index++) {
            if (containerList[index].attrs.song.id == songList[index].id) {
                // no need to update
                item = containerList[index];
                item.attrs.index = index // fix for drag and drop
            } else {
                // replace
                miss += 1
                item = new SongItem(this.attrs.container, index, songList[index])
                containerList[index] = item
            }

            item.updateActive(current_id)

            // if too many are being replaced
            //if (miss > .3 * containerList.length) {
            //    break;
            //}
        }

        // remove excess
        const removeCount = containerList.length - index
        if (removeCount > 0) {
            containerList.splice(index, removeCount);
        }

        // append new
        for (; index < songList.length; index++) {
            item = new SongItem(this.attrs.container, index, songList[index])
            containerList.push(item)
            item.updateActive(current_id)
            miss += 1
        }

        if (miss > 0) {
            this.attrs.container.update()
        }

        console.log("miss rate", hit, miss)


    }
 }