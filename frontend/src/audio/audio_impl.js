
import api

let device_instance = null;
let audio_instance = null;

export class AudioDevice {


    // https://www.w3schools.com/tags/ref_av_dom.asp
    constructor() {
        this.connected_elements = []
    }

    mount() {
        //const document_root = document.getElementById("root");
        //document_root.appendChild(audio_instance);
    }

    queueSet(songList) {

    }

    queueLoad() {
        // returns a promise containing the list of songs in the current queue
        return api.queueGetQueue()
    }

    queueCreate(query) {
        // returns a promise containing the list of songs in the current queue
        return api.queueCreate(query)
    }

    playSong(song) {
        const url = api.librarySongAudioUrl(song.id);

        audio_instance.src = url;

        audio_instance.volume = .5

        audio_instance.play()
    }

    playIndex(index) {
        //
        //
    }

    togglePlayPause() {
        if (this.isPlaying()) {
            audio_instance.pause()
        } else {
            audio_instance.play()
        }
    }

    setVolume(volume) {

        audio_instance.volume = volume
    }

    isPlaying() {
        return audio_instance
            && audio_instance.currentTime > 0
            && !audio_instance.paused
            && !audio_instance.ended
            && audio_instance.readyState > 2;
    }

    // ---------

    connectView(elem) {
        // element is a DomElement instance which implements one of
        // the following signal events. If the element is no longer
        // mounted then it is  automatically disconnected
        this.connected_elements.push(elem)
        console.log(`connect '${elem.props.id}'`)

    }

    disconnectView(elem) {

        this.connected_elements = this.connected_elements.filter(e => e===elem)
        console.log(`disconnect '${elem.props.id}'`)
    }

    _sendEvent(eventname, event) {
        this.connected_elements = this.connected_elements.filter(e => e.isMounted())

        this.connected_elements.forEach(e => {
            if (e && e[eventname]) {
                e[eventname](event);
            }
        })
    }

    // ---------

    onplay(event) {
        //console.log(event)
        this._sendEvent('handleAudioPlay', event)
    }

    onpause(event) {
        //console.log(event)
        this._sendEvent('handleAudioPause', event)
    }

    onwaiting(event) {
        //console.log(event)
        this._sendEvent('handleAudioWaiting', event)
    }

    onstalled(event) {
        //console.log(event)
        this._sendEvent('handleAudioStalled', event)
    }

    ontimeupdate(event) {
        //console.log(event)
        this._sendEvent('handleAudioTimeUpdate', event)
    }

    ondurationchange(event) {
        // audio_instance.duration
        this._sendEvent('handleAudioDurationChange', event)
    }

    onended(event) {
        //console.log(event)
        this._sendEvent('handleAudioEnded', event)
    }


}

AudioDevice.instance = function() {
    if (device_instance === null) {
        device_instance = new AudioDevice()
        audio_instance = new Audio();

        const bind = (x) => audio_instance['on' + x] = device_instance['on' + x].bind(device_instance);

        bind('play');
        bind('pause');
        bind('durationchange');
        bind('timeupdate');
        bind('waiting');
        bind('stalled');
        bind('ended');
    }
    return device_instance;
}