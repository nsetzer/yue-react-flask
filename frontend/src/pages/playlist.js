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
        top:0
    }),

    toolbar: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'justify-content': 'flex-start',
        'align-items': 'center',
        width: '100%'
    }),

    songItem: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'padding-left': '1.1em',
        'padding-bottom': '.5em',
        //width: '100%',
        border: {style: "solid", width: "1px"}
    }),

    fontBig: StyleSheet({
        'font-size': "120%"
    }),

    fontSmall: StyleSheet({
        'font-size': "80%"
    })
}


StyleSheet(`.${style.songItem}:hover`, {background: '#0000FF22'})



class SongItem extends DomElement {
    constructor(index, song) {
        super("div", {className: style.songItem}, []);

        this.attrs = {
            index,
            song,
        }

        const txt1 = this.appendChild(new components.MiddleText((index+1) + ". " + song.title))
        txt1.addClassName(style.fontBig)
        const txt2 = this.appendChild(new components.MiddleText(song.artist))
        txt2.addClassName(style.fontSmall)

    }

    onClick() {

        console.log(this.attrs.index)
        audio.AudioDevice.instance().playSong(this.attrs.song)
    }
}

class Header extends DomElement {
    constructor(parent) {
        super("div", {className: style.header}, []);

        this.attrs = {
            parent,
            toolbar: new DomElement("div", {className: style.toolbar}, [])
        }

        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_prev'], ()=>{

        }))
        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_play'], ()=>{
            audio.AudioDevice.instance().togglePlayPause()
        }))
        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_next'], ()=>{

        }))
        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_shuffle'], ()=>{
            audio.AudioDevice.instance().queueCreate("")
                .then(this.attrs.parent.showQueue.bind(this))
                .catch(this.attrs.parent.showQueueError.bind(this))

        }))

        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_shuffle'], ()=>{
            audio.AudioDevice.instance().queueCreate("genre = stoner")
                .then(this.attrs.parent.showQueue.bind(this.attrs.parent))
                .catch(this.attrs.parent.showQueueError.bind(this.attrs.parent))

        }))

        this.attrs.toolbar.appendChild(new components.SvgButtonElement(resources.svg['media_shuffle'], ()=>{
            audio.AudioDevice.instance().queueCreate('("visual kei" || genre=j-metal ||(genre =j-rock && genre = "nu metal")) && rating > 0')
                .then(this.attrs.parent.showQueue.bind(this.attrs.parent))
                .catch(this.attrs.parent.showQueueError.bind(this.attrs.parent))

        }))

        this.appendChild(this.attrs.toolbar)
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
        this.attrs.device.queueLoad()
            .then(this.showQueue.bind(this))
            .catch(this.showQueueError.bind(this))

        this.attrs.device.connectView(this)
    }

    elementUnmounted() {
        console.log("dismount playlist view")

        this.attrs.device.disconnectView(this)
    }

    showQueue(queue) {

        this.attrs.container.removeChildren()

        queue.result.forEach((song, index) => {
            this.attrs.container.appendChild(new SongItem(index, song))
        })

        this.update()

        this.attrs.device.queueSet(queue.result)

    }

    showQueueError(error) {

        this.attrs.container.removeChildren()
        this.attrs.container.appendChild(new TextElement("Error..."))
    }

    handleAudioPlay(event) {
        console.log("on play")
    }

    handleAudioPause(event) {
        console.log("on pause")
    }
}