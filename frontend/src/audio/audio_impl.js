
import module api

let device_instance = null;
let audio_instance = null;

export class AudioDevice {


    // https://www.w3schools.com/tags/ref_av_dom.asp
    constructor() {
        this.connected_elements = [];
        this.current_index = -1;
        this.current_song = null;
        this.queue = []
    }

    mount() {
        //const document_root = document.getElementById("root");
        //document_root.appendChild(audio_instance);
    }

    queueGet() {
        return this.queue
    }

    queueLength() {
        return this.queue.length
    }

    queueSet(songList) {
        this.queue = songList

        this.stop();
    }

    queueSave() {
        // TODO: implement event for save success/fail
        const idList = this.queue.map(song => song.id).filter(uuid => !!uuid)
        api.queueSetQueue(idList)
            .then(result => {console.log(result)})
            .catch(result => {console.log(result)})
    }

    queueLoad() {
        // returns a promise containing the list of songs in the current queue
        api.queueGetQueue()
            .then(result => {
                this.queue = result.result
                this._sendEvent('handleAudioQueueChanged', result.result)
            })
            .catch(error => {
                console.log(error);
                this._sendEvent('handleAudioQueueChanged', [])
            })
        this.stop()
    }

    queueCreate(query) {
        // returns a promise containing the list of songs in the current queue
        api.queueCreate(query, 50)
            .then(result => {
                this.queue = result.result
                this._sendEvent('handleAudioQueueChanged', result.result)
            })
            .catch(error => {
                console.log(error);
                this._sendEvent('handleAudioQueueChanged', [])
            })
        this.stop()
    }

    queueMoveSongUp(index) {

        if (index >= 1 && index < this.queue.length) {
            const target = index - 1

            const a = this.queue.splice(index, 1);
            this.queue.splice(target, 0, a[0]);

            if (this.current_index == index) {
                this.current_index = target;
            } else if (this.current_index == target) {
                this.current_index += 1;
            }
            //console.log("move", index, target)
            this._sendEvent('handleAudioQueueChanged', this.queue)
        }

    }

    queueMoveSongDown(index) {
        if (index >= 0 && index < this.queue.length - 1) {
            const target = index + 1

            const a = this.queue.splice(index, 1);
            this.queue.splice(target, 0, a[0]);

            if (this.current_index == index) {
                this.current_index = target;
            } else if (this.current_index == target) {
                this.current_index -= 1;
            }
            //console.log("move", index, target)
            this._sendEvent('handleAudioQueueChanged', this.queue)
        }
    }

    queuePlayNext(song) {

        const index = this.current_index + 1
        console.log(0, index, this.queue.length, index >= 0 && index < this.queue.length)
        if (index >= 0 && index < this.queue.length) {
            this.queue.splice(index, 0, song)
        } else if (index >= this.queue.length) {
            this.queue.push(song)
        } else {
            // user must click next to play
            this.current_index = -1;
            this.current_song = song;
            this.queue = [song,]
            this._sendEvent('handleAudioSongChanged', null);
        }
        this._sendEvent('handleAudioQueueChanged', this.queue)
        console.log(this.queue)
    }

    queueRemoveIndex(index) {
        if (index >= 0 && index < this.queue.length) {
            const a = this.queue.splice(index, 1);

            if (index >= this.queue.length) {
                this.pause();
                this.current_index = -1;
                this.current_song = null;
                this._sendEvent('handleAudioSongChanged', null);

            } else if (index == this.current_index) {
                this.pause();
                this.current_song = this.queue[index];
                this._sendEvent('handleAudioSongChanged', this.queue[index]);
            } else if (index < this.current_index) {
                this.current_index -= 1;
                this.current_song = this.queue[index];
            }

            this._sendEvent('handleAudioQueueChanged', this.queue)
        }
    }

    stop() {
        if (this.isPlaying()) {
            this.pause()
        }

        this.current_index = -1
        this.current_song = null;
        this._sendEvent('handleAudioSongChanged', null)
    }

    pause() {
        if (this.isPlaying()) {
            audio_instance.pause()
        }
    }

    _playSong(song) {

        this.current_song = song

        const url = api.librarySongAudioUrl(song.id);

        audio_instance.src = url;

        audio_instance.volume = .75

        audio_instance.play()

        // current_index must be set prior to calling this function
        this._sendEvent('handleAudioSongChanged', {...song, index: this.current_index})
    }

    playSong(song) {
        this.current_index = -1;
        this._playSong(song);
    }

    playIndex(index) {
        if (index >= 0 && index < this.queue.length) {
            this.current_index = index
            this._playSong(this.queue[index])
        } else {
            this.current_index = -1
            this.current_song = null;
            this.stop()
            this._sendEvent('handleAudioSongChanged', null)
            console.warn("invalid playlist index " + index)
        }
    }

    togglePlayPause() {
        if (this.isPlaying()) {
            audio_instance.pause()
        } else {
            audio_instance.play()
        }
    }

    next() {
        const idx = this.current_index + 1
        if (idx >= 0 && idx < this.queue.length) {
            this.playIndex(idx)
        }
    }

    prev() {
        const idx = this.current_index - 1
        if (idx >= 0 && idx < this.queue.length) {
            this.playIndex(idx)
        }
    }

    currentSongId() {
        const idx = this.current_index;
        if (idx >= 0 && idx < this.queue.length) {
            return this.queue[idx].id;
        }
        return null;
    }
    currentTime() {
        return audio_instance.currentTime;
    }

    setCurrentTime(time) {
        console.log(time)
        audio_instance.currentTime = time;
    }

    duration() {
        return audio_instance.duration;
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
        if (this.connected_elements.filter(e => e===elem).length > 0) {
            console.error("already connected view");
            return;
        }

        this.connected_elements.push(elem)
        //console.log(`connect '${elem.props.id}'`)

    }

    disconnectView(elem) {

        this.connected_elements = this.connected_elements.filter(e => e!==elem)
        //console.log(`disconnect '${elem.props.id}'`)
    }

    // todo: this 'signal and slot' mechanism is better than the previous impl
    //
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
        this._sendEvent('handleAudioPlay', {})
    }

    onpause(event) {
        //console.log(event)
        this._sendEvent('handleAudioPause', {})
    }

    onwaiting(event) {
        //console.log(event)
        this._sendEvent('handleAudioWaiting', {})
    }

    onstalled(event) {
        //console.log(event)
        this._sendEvent('handleAudioStalled', {})
    }

    ontimeupdate(event) {
        //console.log(event)
        this._sendEvent('handleAudioTimeUpdate', {
            currentTime: audio_instance.currentTime,
            duration: audio_instance.duration
        })
    }

    ondurationchange(event) {
        // audio_instance.duration
        this._sendEvent('handleAudioDurationChange', {
            currentTime: audio_instance.currentTime,
            duration: audio_instance.duration
        })
    }

    onended(event) {
        console.log("on ended", this.current_index)
        this._sendEvent('handleAudioEnded', event)

        this.next()


    }


}

/*

setting currentTime on android does not work. one of these
alternatives may work

function Video(src, append) {
  var v = document.createElement("video");
  if (src != "") {
    v.src = src;
  }
  if (append == true) {
    document.body.appendChild(v);
  }
  return v;
}

Java:
    if (url.endsWith(".ogg")){
        Uri tempPath = Uri.parse(url);
        MediaPlayer player = MediaPlayer.create(WebViewVideo.this, tempPath);
        player.start();
        return true;
    }

}
*/

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