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

    songList: StyleSheet({
        'padding-left': '1em',
        'padding-right': '1em',
    }),

    songItem: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        margin-bottom: '.25em',
        border: {style: "solid", width: "1px"},
        width: 'calc(100% - 2px)', // minus border width * 2
    }),

    songItemPlaceholder: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        margin-bottom: '.25em',
        border: {style: "solid", width: "1px"},
        //background-color: "#edf2f7",
        border: "1px solid black",

        background-position: '0px 0px, 10px 10px',
        background-size: '20px 20px',
        background-image: 'linear-gradient(45deg, #eee 25%, transparent 25%, transparent 75%, #eee 75%, #eee 100%),linear-gradient(45deg, #eee 25%, white 25%, white 75%, #eee 75%, #eee 100%)'

    }),

    songItemActive: StyleSheet({
        background: '#00FF0022',
    }),

    fontBig: StyleSheet({
        'font-size': "110%"
    }),

    fontSmall: StyleSheet({
        'font-size': "85%"
    }),

    songItemRow: StyleSheet({
        display:'flex',
        'flex-direction': 'row',
        width: '100%'
    }),
    songItemRhs: StyleSheet({
        'flex': '1 1 0',
        // 100% minus grip + padding
        'max-width': 'calc(100% - 1.5em)'
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
        width: "1em",
        min-width: "1em",
        //height: "2em",
        background: "linear-gradient(rgba(0,0,0,0) 30%, rgba(0,0,0,.3) 40%, rgba(0,0,0,0) 50%, rgba(0,0,0,.3) 60%, rgba(0,0,0,0) 70%);",
    }),
    space5 : StyleSheet({width: ".25em", min-width: ".25em"}),

    center80: StyleSheet({max-width: '80%'}),

    lockScreen: StyleSheet({
        height: '100%',
        overflow: 'hidden',
        width: '100%',
        position: 'fixed',
    })

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


        //const div2 = this.appendChild(new DomElement("div", {className: style.songItemRow}, []))

        this.appendChild(new DomElement("div", {className:style.space5}, []) )
        const grip = this.appendChild(new DomElement("div", {className:style.grip}, []) )
        this.appendChild(new DomElement("div", {className:style.space5}, []) )

        grip.props.onMouseDown = (event) => {
            let node = this.getDomNode()
            node.style.width = node.clientWidth + 'px'
            node.style.background = "white"
            this.attrs.parent.handleChildDragBegin(this, event)

            //node.style.left = '0px'
            //node.style.right = '0px'


            event.stopPropagation()
        }

        grip.props.onTouchStart = (event) => {
            let node = this.getDomNode()
            node.style.width = node.clientWidth + 'px'
            node.style.background = "white"
            this.attrs.parent.handleChildDragBegin(this, event)

            event.stopPropagation()
        }

        const divrhs = this.appendChild(new DomElement("div", {className:style.songItemRhs}, []))

        //const divrhs = this

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
        //this.attrs.toolbar.appendChild(new CallbackLink2("move up", ()=>{
        //    audio.AudioDevice.instance().queueMoveSongUp(this.attrs.index)
        //}))
        //this.attrs.toolbar.appendChild(new CallbackLink2("move down", ()=>{
        //    audio.AudioDevice.instance().queueMoveSongDown(this.attrs.index)
        //}))
        //this.attrs.toolbar.appendChild(new CallbackLink2("delete", ()=>{
        //    audio.AudioDevice.instance().queueRemoveIndex(this.attrs.index)
        //}))


        divrhs.appendChild(this.attrs.toolbar)

    }

    setIndex(index) {
        if (index != this.attrs.index) {
            this.attrs.index = index
            this.attrs.txt1.setText((index+1) + ". " + this.attrs.song.title)
        }
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

    onTouchStart(event) {
        let node = this.getDomNode()
        node.style.width = node.clientWidth + 'px'
        node.style.background = "white"
        this.attrs.parent.handleChildSwipeBegin(this, event)
        event.stopPropagation()
    }

    onMouseDown(event) {
        let node = this.getDomNode()
        node.style.width = node.clientWidth + 'px'
        node.style.background = "white"
        this.attrs.parent.handleChildSwipeBegin(this, event)
        event.stopPropagation()
    }

    onTouchMove(event) {
        if (this.attrs.parent.attrs.isSwipe) {
            if (!this.attrs.parent.handleChildSwipeMove(this, event)) {
                return;
            }
        } else {
            this.attrs.parent.handleChildDragMove(this, event)
        }
        event.stopPropagation()
        //this.setIndex(99)
    }

    onTouchEnd(event) {
        if (this.attrs.parent.attrs.isSwipe) {
            this.attrs.parent.handleChildSwipeEnd(this, {target: this.getDomNode()})
        } else {
            this.attrs.parent.handleChildDragEnd(this, {target: this.getDomNode()})
            let node = this.getDomNode()
            node.style.removeProperty('width');
            node.style.removeProperty('background');
        }

        event.stopPropagation()
    }

    onTouchCancel(event) {
        if (this.attrs.parent.attrs.isSwipe) {
            this.attrs.parent.handleChildSwipeEnd(this, {target: this.getDomNode()})
        } else {
            this.attrs.parent.handleChildDragEnd(this, {target: this.getDomNode()})
            let node = this.getDomNode()
            node.style.removeProperty('width');
            node.style.removeProperty('background');
        }

        event.stopPropagation()
    }

    onMouseMove(event) {
        if (this.attrs.parent.attrs.isSwipe) {
            if(!this.attrs.parent.handleChildSwipeMove(this, event)) {
                return
            }
        } else {
            this.attrs.parent.handleChildDragMove(this, event)
        }

        event.stopPropagation()
    }

    onMouseLeave(event) {
        if (this.attrs.parent.attrs.isSwipe) {
            this.attrs.parent.handleChildSwipeCancel(this, event)
        } else {
            this.attrs.parent.handleChildDragMove(this, event)
            let node = this.getDomNode()
            node.style.removeProperty('width');
            node.style.removeProperty('background');
        }

        event.stopPropagation()
    }

    onMouseUp(event) {

        if (this.attrs.parent.attrs.isSwipe) {
            this.attrs.parent.handleChildSwipeEnd(this, event)
        } else {
            this.attrs.parent.handleChildDragEnd(this, event)
            let node = this.getDomNode()
            node.style.removeProperty('width');
            node.style.removeProperty('background');
        }


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
        this.attrs.txt_SongStatus = new TextElement("")

        this.addRow(true)
        this.addRow(true)
        this.addRow(true)

        this.addRowElement(0, this.attrs.txt_SongTitle)
        this.addRowElement(1, this.attrs.txt_SongTime)
        this.addRowElement(2, this.attrs.txt_SongStatus)

        this.attrs.txt_SongTitle.addClassName(style.center80)

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

    setStatus(status) {
        this.attrs.txt_SongStatus.setText(status)
    }

}

const SWIPE_RIGHT = 0x01;
const SWIPE_LEFT  = 0x02;

class SongList extends daedalus.DraggableList {

    constructor() {
        super()

        // flip between drag and drop and swipe mode
        this.attrs.isSwipe = false;
        // true when an animation is present and actions should be ignored
        this.attrs.isAnimated = false;

        // pointer to child object which was swipped right or left
        this.attrs.swipeActionRight = null;
        this.attrs.swipeActionLeft = null;

        this.attrs.swipeConfig = SWIPE_RIGHT;

    }
    updateModel(indexStart, indexEnd) {
        super.updateModel(indexStart, indexEnd);

        audio.AudioDevice.instance().queueSwapSong(indexStart, indexEnd)
    }

    handleChildDragBegin(child, event) {
        if (this.attrs.isAnimated) {
            return
        }
        super.handleChildDragBegin(child, event);
        this.attrs.isSwipe = false;
    }

    handleChildDragMove(child, event) {
        if (this.attrs.isAnimated) {
            return
        }
        super.handleChildDragMove(child, event);
        this.attrs.isSwipe = false;
    }

    handleChildSwipeBegin(child, event) {
        if (this.attrs.isAnimated) {
            return
        }

        if (!!this.attrs.draggingEle) {
            // previous drag did not complete. cancel that drag and ignore
            // this event
            this.handleChildSwipeCancel(child, event);
            return;
        }

        const org_event = event;

        let evt = (event?.touches || event?.originalEvent?.touches)
        if (evt) {
            event = evt[0]
        }

        const draggingEle = child.getDomNode();
        const rect = draggingEle.getBoundingClientRect();
        const x = event.pageX - rect.left
        const y = event.pageY - rect.top

        let pos = Math.abs(Math.floor(100 * (x / (rect.right - rect.left))))

        if ( pos > 30 && pos < 70 ) {
            org_event.preventDefault()


            this.attrs.draggingEle = draggingEle;
            // Calculate the mouse position
            this.attrs.xstart = rect.left;
            this.attrs.ystart = rect.top;
            this.attrs.x = x;
            this.attrs.y = y;

            this.attrs.isSwipe = true;
        }
    }

    handleChildSwipeMove(child, event) {

        if (this.attrs.isAnimated) {
            return
        }

        if (this.attrs.draggingEle!==child.getDomNode()) {
            return;
        }

        let org_event = event;

        let evt = (event?.touches || event?.originalEvent?.touches)
        if (evt) {


            event = evt[0]

            // cancel touch events outside the widget
            if (event.pageY < this.attrs.draggingEle.offsetTop ||
                event.pageY > this.attrs.draggingEle.offsetTop + this.attrs.draggingEle.clientHeight) {
                this.handleChildSwipeCancel(child, event)
                return;
            }
        }

        let deltax = event.pageX - this.attrs.xstart - this.attrs.x
        //let deltay = event.pageY - this.attrs.ystart - this.attrs.y;


        if (!this.attrs.isDraggingStarted) {

            const draggingRect = this.attrs.draggingEle.getBoundingClientRect();

            if (Math.abs(deltax) < 32) {
                return false;
            }

            this.attrs.isDraggingStarted = true;


            this.attrs.draggingEle.style.removeProperty('transition');

            // Let the placeholder take the height of dragging element
            // So the next element won't move up
            this.attrs.placeholder = document.createElement('div');
            this.attrs.placeholder.classList.add(this.attrs.placeholderClassName);
            this.attrs.draggingEle.parentNode.insertBefore(this.attrs.placeholder, this.attrs.draggingEle.nextSibling);
            this.attrs.placeholder.style.height = `${draggingRect.height-2}px`;  // minus border top / bot

        }

        org_event.preventDefault()

        this.attrs.draggingEle.style.position = 'absolute';
        this.attrs.draggingEle.style.left = `${event.pageX - this.attrs.x}px`;
        //this.attrs.draggingEle.style['touch-action'] = 'none';

        return true;
    }

    handleChildSwipeEnd(child, event) {
        this.handleChildSwipeCancel(child, event, true);
    }

    handleChildSwipeCancel(child, event, success=false) {
        // Remove the placeholder

        if (this.attrs.draggingEle!==child.getDomNode()) {
            return;
        }

        if (this.attrs.isAnimated) {
            return
        }

        let deltax = this.attrs.draggingEle.offsetLeft - this.attrs.placeholder.offsetLeft

        // minimum drag distance to force a delete
        const SWIPE_OFFSET = 32

        // TODO: cancel when touch event is not within bounding box of item

        const cfg = this.attrs.swipeConfig

        if (success && deltax > SWIPE_OFFSET && cfg&SWIPE_RIGHT) {
            this.attrs.draggingEle.style.left = `${document.body.clientWidth}px`
            this.swipeActionRight = child;
        } else if (success && deltax < SWIPE_OFFSET && cfg&SWIPE_LEFT) {
            this.attrs.draggingEle.style.left = `${-this.attrs.draggingEle.clientWidth}px`
            this.swipeActionLeft = child;
        } else {
            this.attrs.draggingEle.style.left = this.attrs.placeholder.offsetLeft + 'px'
        }
        this.attrs.draggingEle.style.transition = 'left .35s'
        setTimeout(this.handleChildSwipeTimeout.bind(this), 350)
        this.attrs.isAnimated = true
    }

    handleChildSwipeTimeout() {
        console.log("swipe timeout")
        this.attrs.isAnimated = false
        this.attrs.x = null;
        this.attrs.y = null;
        this.attrs.isDraggingStarted = false;

        if (this.attrs.placeholder && this.attrs.placeholder.parentNode) {
            this.attrs.placeholder.parentNode.removeChild(this.attrs.placeholder);
        }


        if (!this.attrs.draggingEle) {
            return
        }

        this.attrs.draggingEle.style.removeProperty('left');
        this.attrs.draggingEle.style.removeProperty('position');
        this.attrs.draggingEle.style.removeProperty('transition');
        this.attrs.draggingEle.style.removeProperty('width');
        this.attrs.draggingEle.style.removeProperty('background');

        this.attrs.draggingEle = null;

        if (!!this.swipeActionRight) {
            this.handleSwipeRight(this.swipeActionRight)
            this.swipeActionRight = null;
        }

        if (!!this.swipeActionLeft) {
            this.handleSwipeLeft(this.swipeActionLeft)
            this.swipeActionLeft = null;
        }

    }

    handleSwipeRight(child) {
        console.log("handle swipe right", child);
        const index = child.attrs.index
        audio.AudioDevice.instance().queueRemoveIndex(index)
    }

    handleSwipeLeft(child) {
        console.log("handle swipe left");
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
        this.attrs.container.addClassName(style.songList)

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
        this.attrs.header.setStatus("playing")
    }

    handleAudioPause(event) {
        this.attrs.header.setStatus("paused")
    }

    handleAudioWaiting(event) {
        this.attrs.header.setStatus("waiting")
    }

    handleAudioStalled(event) {
        this.attrs.header.setStatus("stalled")
    }

    handleAudioEnded(event) {
        this.attrs.header.setStatus("ended")
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
        let del = 0;
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
                item.setIndex(index) // fix for drag and drop
            } else if (index < (containerList.length - 1) && containerList[index+1].attrs.song.id == songList[index].id) {
                // optimization for delete of a single row element
                containerList.splice(index, 1)
                item = containerList[index];
                item.setIndex(index) // fix for drag and drop
                del += 1
            } else {
                // substitution
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
        console.log("update", containerList.length, songList.length, removeCount, index)
        if (removeCount > 0) {
            containerList.splice(index, removeCount);
            del += removeCount
        }

        // append new
        for (; index < songList.length; index++) {
            item = new SongItem(this.attrs.container, index, songList[index])
            containerList.push(item)
            item.updateActive(current_id)
            miss += 1
        }

        if (miss > 0 || del > 0) {
            this.attrs.container.update()
        }

        console.log("miss rate", hit, miss, del)


    }
 }