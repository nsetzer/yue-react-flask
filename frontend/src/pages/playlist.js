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
import resources
import audio

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

    headerDiv: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%'
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

    txtInput: StyleSheet({width: "80%"}),

    songItem: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'padding-left': '1.1em',
        'padding-bottom': '.5em',
        //width: '100%',
        border: {style: "solid", width: "1px"}
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

    callbackLink2: StyleSheet({
        cursor: 'pointer',
        color: 'blue',
        'padding-right': '1em'
    }),
}


StyleSheet(`.${style.songItem}:hover`, {background: '#0000FF22'})

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
    constructor(index, song) {
        super("div", {className: style.songItem}, []);

        this.attrs = {
            index,
            song,
            active: false,
            toolbar: new DomElement("div", {className:style.toolbar}, [])
        }

        this.attrs.txt1 = this.appendChild(new components.MiddleText((index+1) + ". " + song.title))
        this.attrs.txt1.addClassName(style.fontBig)
        this.attrs.txt2 = this.appendChild(new components.MiddleText(song.artist))
        this.attrs.txt2.addClassName(style.fontSmall)


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

        this.appendChild(this.attrs.toolbar)

    }

    //onClick() {
    //    console.log(this.attrs.index)
    //    audio.AudioDevice.instance().playIndex(this.attrs.index)
    //}

    updateActive(id) {
        if (id === undefined) {
            console.error("err undef")
            return
        }
        const active = id === this.attrs.song.id
        if (this.attrs.active != active) {
            this.attrs.active = active
            if (active) {
                this.attrs.txt1.setText((this.attrs.index+1) + ". *** " + this.attrs.song.title)
                this.addClassName(style.songItemActive)
            } else {
                this.removeClassName(style.songItemActive)
                this.attrs.txt1.setText((this.attrs.index+1) + ". " + this.attrs.song.title)
            }
        }
    }
}

function formatTime(secs) {
    secs = secs===Infinity?0:secs
    var minutes = Math.floor(secs / 60) || 0;
    var seconds = Math.floor(secs - minutes * 60) || 0;
    return minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
}

class Header extends DomElement {
    constructor(parent) {
        super("div", {className: style.header}, []);

        this.attrs = {
            parent,
            toolbar: new DomElement("div", {className: style.toolbar}, []),
            txtInput: new TextInputElement(""),
            info1: new DomElement("div", {className: style.info}, []),
            info2: new DomElement("div", {className: style.info}, []),
            div: new DomElement("div", {className: style.headerDiv}, [])
        }

        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_prev'], ()=>{
            audio.AudioDevice.instance().prev()
        }))
        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_play'], ()=>{
            audio.AudioDevice.instance().togglePlayPause()
        }))
        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_next'], ()=>{
            audio.AudioDevice.instance().next()
        }))
        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_shuffle'], ()=>{
            audio.AudioDevice.instance().queueCreate(this.attrs.txtInput.props.value)
        }))

        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_shuffle'], ()=>{
            audio.AudioDevice.instance().queueCreate("genre = stoner")
        }))

        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_shuffle'], ()=>{
            audio.AudioDevice.instance().queueCreate('("visual kei" || genre=j-metal ||(genre =j-rock && genre = "nu metal")) && rating > 0')
        }))

        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['save'], ()=>{
            audio.AudioDevice.instance().queueSave()
        }))

        this.attrs.txtInput.addClassName(style.txtInput)
        this.attrs.txt_SongTitle = this.attrs.info1.appendChild(new components.MiddleText("Select A Song"))
        this.attrs.txt_SongTime = this.attrs.info2.appendChild(new TextElement("00:00:00/00:00:00"))

        this.appendChild(this.attrs.div)
        this.attrs.div.appendChild(this.attrs.toolbar)
        this.attrs.div.appendChild(this.attrs.txtInput)
        this.attrs.div.appendChild(this.attrs.info1)
        this.attrs.div.appendChild(this.attrs.info2)

        this.attrs.info2.props.onClick = () => {
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

export class PlaylistPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            device: audio.AudioDevice.instance(),
            header: new Header(this),
            container: new DomElement("div", {}, [new TextElement("Loading...")])
        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.container)

    }

    elementMounted() {
        console.log("mount playlist view")

        this.attrs.device.connectView(this)

        if (this.attrs.device.queueLength()==0) {
            this.attrs.device.queueLoad()
        }


    }

    elementUnmounted() {
        console.log("dismount playlist view")

        this.attrs.device.disconnectView(this)
    }

    xshowQueue(queue) {

        this.attrs.container.removeChildren()

        queue.result.forEach((song, index) => {
            this.attrs.container.appendChild(new SongItem(index, song))
        })

        this.update()

        this.attrs.device.queueSet(queue.result)
    }

    xshowQueueError(error) {

        console.error(error)
        this.attrs.container.removeChildren()
        this.attrs.container.appendChild(new TextElement("Error..."))
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
        this.attrs.container.removeChildren()

        const current_id = audio.AudioDevice.instance().currentSongId();
        songList.forEach((song, index) => {
            const item = new SongItem(index, song)
            this.attrs.container.appendChild(item)
            item.updateActive(current_id)
        })

    }
 }