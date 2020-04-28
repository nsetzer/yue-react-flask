
// todo: rename device -> manager

import module api

let device_instance = null;

class RemoteDeviceImpl {

    constructor(device) {
        this.device = device

        this.audio_instance = new Audio();

        this.auto_play = false;

        const bind = (x) => {this.audio_instance['on' + x] = this['on' + x].bind(this)};

        bind('play');
        bind('loadstart');
        bind('playing');
        bind('pause');
        bind('durationchange');
        bind('timeupdate');
        bind('waiting');
        bind('stalled');
        bind('ended');
        bind('error');
    }

    setQueue(queue) {
        // TODO: implement event for save success/fail
        const idList = queue.map(song => song.id).filter(uuid => !!uuid)
        api.queueSetQueue(idList)
            .then(result => {console.log(result)})
            .catch(result => {console.log(result)})

        this.device._sendEvent('handleAudioQueueChanged', queue)
    }

    updateQueue(index, queue) {



    }

    loadQueue() {
        return api.queueGetQueue()
    }

    createQueue(query) {

        return api.queueCreate(query, 50)
    }

    playSong(index, song) {

        const url = api.librarySongAudioUrl(song.id);

        this.audio_instance.src = url
        this.audio_instance.volume = .75

        this.auto_play = true;

    }

    play() {
        this.audio_instance.play()
    }

    stop() {
        if (this.isPlaying()) {
            this.pause()
        }


        this.device._sendEvent('handleAudioSongChanged', null)
    }

    pause() {
        if (this.isPlaying()) {
            this.audio_instance.pause()
        }
    }

    currentTime() {
        return this.audio_instance.currentTime;
    }

    setCurrentTime(time) {
        // TODO: check that time is finite
        // index.js:2052 Uncaught TypeError: Failed to set the 'currentTime' property on 'HTMLMediaElement': The provided double value is non-finite.
        this.audio_instance.currentTime = time;
    }

    duration() {
        return this.audio_instance.duration;
    }

    setVolume(volume) {

        this.audio_instance.volume = volume
    }

    isPlaying() {
        return this.audio_instance
            && this.audio_instance.currentTime > 0
            && !this.audio_instance.paused
            && !this.audio_instance.ended
            && this.audio_instance.readyState > 2;
    }


    // ---------

    onloadstart(event) {
        console.log('audio on load start')
        if (this.auto_play) {
            this.audio_instance.play()
        }
        this.device._sendEvent('handleAudioLoadStart', {})
    }

    onplay(event) {
        //console.log(event)
        this.device._sendEvent('handleAudioPlay', {})
    }

    onplaying(event) {
        console.log("playing", event)
        this.device._sendEvent('handleAudioPlay', {})
    }

    onpause(event) {
        //console.log(event)
        this.device._sendEvent('handleAudioPause', {})
    }

    onwaiting(event) {
        //console.log(event)
        this.device._sendEvent('handleAudioWaiting', {})
    }

    onstalled(event) {
        //console.log(event)
        this.device._sendEvent('handleAudioStalled', {})
    }

    ontimeupdate(event) {
        //console.log(event)
        this.device._sendEvent('handleAudioTimeUpdate', {
            currentTime: this.audio_instance.currentTime,
            duration: this.audio_instance.duration
        })
    }

    ondurationchange(event) {
        // audio_instance.duration
        this.device._sendEvent('handleAudioDurationChange', {
            currentTime: this.audio_instance.currentTime,
            duration: this.audio_instance.duration
        })
    }

    onended(event) {
        console.log("on ended", this.current_index)
        this.device._sendEvent('handleAudioEnded', event)

        this.next()

    }

    onerror(event) {
        console.log("on error", this.current_index)
        this.device._sendEvent('handleAudioError', event)

        this.next()

    }
}

function mapSongToObj(song) {
    return {
        url: api.librarySongAudioUrl(song.id),
        artist: song.artist,
        album: song.album,
        title: song.title,
        length: song.length,
        id: song.id,
    }
}
class NativeDeviceImpl {

    constructor(device) {
        this.device = device

        console.error("-------------------------------------");
        const bind = (x) => {
            registerAndroidEvent('on' + x, this['on' + x].bind(this))
        };

        bind('prepared');
        bind('play');
        bind('pause');
        bind('stop');
        bind('error');
        bind('timeupdate');
        bind('indexchanged');

    }

    setQueue(queue) {
        console.log("setting queue")
        return new Promise((accept, reject) => {
            const lst = queue.map(mapSongToObj);
            const data = JSON.stringify(lst)
            AndroidNativeAudio.setQueue(data);
            this.device._sendEvent('handleAudioQueueChanged', queue)
            accept(true);
        })
    }

    updateQueue(index, queue) {
        console.log("updating queue")
        return new Promise((accept, reject) => {
            const lst = queue.map(mapSongToObj);
            const data = JSON.stringify(lst)
            AndroidNativeAudio.updateQueue(index, data);
            accept(true);
        })
    }

    loadQueue() {
        console.log("loading queue")
        return new Promise((accept, reject) => {
            console.log("loading queue: from promise")
            let data;
            try {
                data = AndroidNativeAudio.getQueue()
            } catch (e) {
                console.error("load queue error: " + e.message)
            }
            if (data.length > 0) {
                let tracks = JSON.parse(data)
                console.log("loading queue: " + tracks.length);
                accept({result: tracks})
            } else {
                console.log("loading queue: error");
                accept({result: []})
            }

        })
    }

    createQueue(query) {
        return api.queueCreate(query, 50)
    }

    playSong(index, song) {
        AndroidNativeAudio.loadIndex(index)
    }

    play() {
        AndroidNativeAudio.play();
    }

    pause() {
        AndroidNativeAudio.pause();
    }

    stop() {
        AndroidNativeAudio.stop();

        this.device._sendEvent('handleAudioSongChanged', null)
    }

    currentTime() {
        return 0
    }

    setCurrentTime(time) {
        return;
    }

    duration() {
        return 0;
    }

    setVolume(volume) {
        return;
    }

    isPlaying() {
        return AndroidNativeAudio.isPlaying();
    }

    onprepared(payload) {

    }

    onplay(payload) {
        this.device._sendEvent('handleAudioPlay', {})
    }

    onpause(payload) {
        this.device._sendEvent('handleAudioPause', {})
    }

    onstop(payload) {
        this.device._sendEvent('handleAudioStop', {})
    }

    onerror(payload) {

    }

    ontimeupdate(payload) {
        this.device._sendEvent('handleAudioTimeUpdate', {
            currentTime: payload.position / 1000,
            duration: payload.duration / 1000
        })
    }

    onindexchanged(payload) {

        const index = payload.index;

        this.device._sendEvent('handleAudioSongChanged', this.device.queue[index]);
    }

}

export class AudioDevice {

    // https://www.w3schools.com/tags/ref_av_dom.asp
    constructor() {
        this.connected_elements = [];
        this.current_index = -1;
        this.current_song = null;
        this.queue = []

        this.impl = null;
    }

    setImpl(impl) {
        this.impl = impl;
    }

    queueGet() {
        return this.queue
    }

    queueLength() {
        return this.queue.length
    }

    queueSet(songList) {
        this.queue = songList
        this.impl.updateQueue(-1, this.queue)

        this.stop();
    }

    queueSave() {
        this.impl.setQueue(this.queue)
    }

    queueLoad() {
        // returns a promise containing the list of songs in the current queue
        this.impl.loadQueue()
            .then(result => {
                this.queue = result.result
                this._sendEvent('handleAudioQueueChanged', this.queue)
            })
            .catch(error => {
                console.log(error);
                this.queue = []
                this.current_index = -1;
                this._sendEvent('handleAudioQueueChanged', this.queue)
            })
        this.stop()
    }

    queueCreate(query) {
        // returns a promise containing the list of songs in the current queue
        this.impl.createQueue(query)
            .then(result => {
                this.queue = result.result
                this.impl.updateQueue(this.current_index, this.queue)
                this._sendEvent('handleAudioQueueChanged', this.queue)
            })
            .catch(error => {
                console.log(error);
                this.queue = [];
                this.current_index = -1;
                this.impl.updateQueue(this.current_index, this.queue)
                this._sendEvent('handleAudioQueueChanged', this.queue)
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
            this.impl.updateQueue(this.current_index, this.queue)
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
            this.impl.updateQueue(this.current_index, this.queue)
            this._sendEvent('handleAudioQueueChanged', this.queue)
        }
    }

    queueSwapSong(index, target) {

        daedalus.util.array_move(this.queue, index, target)
        if (this.current_index == index) {
            this.current_index = target;
        } else if (index < this.current_index && target >= this.current_index) {
            this.current_index -= 1;
        } else if (index > this.current_index && target <= this.current_index) {
            this.current_index += 1;
        }
        this.impl.updateQueue(this.current_index, this.queue)
        this._sendEvent('handleAudioQueueChanged', this.queue)

    }

    queuePlayNext(song) {

        const index = this.current_index + 1
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
        this.impl.updateQueue(this.current_index, this.queue)
        this._sendEvent('handleAudioQueueChanged', this.queue)
    }

    queueRemoveIndex(index) {
        if (index >= 0 && index < this.queue.length) {
            this.queue.splice(index, 1);
            console.log("queue, sliced", index, this.queue.length)
            if (this.current_index >= this.queue.length) {
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
            console.log("queue, sliced update")
            this.impl.updateQueue(this.current_index, this.queue)
            this._sendEvent('handleAudioQueueChanged', this.queue)
        }
    }

    stop() {
        this.current_index = -1
        this.current_song = null;
        this.impl.stop();
    }

    pause() {
        this.impl.pause();
    }

    _playSong(song) {
        this.current_song = song
        console.log(song)
        this.impl.playSong(this.current_index, this.current_song)

        // current_index must be set prior to calling this function
        this._sendEvent('handleAudioSongChanged', {...song, index: this.current_index})
    }

    playSong(song) {
        this.current_index = -1;
        this._playSong(song);
    }

    playIndex(index) {
        console.log(index)
        if (index >= 0 && index < this.queue.length) {
            this.current_index = index
            this._playSong(this.queue[index])
        } else {
            this.current_index = -1
            this.current_song = null;
            this.stop()
            this._sendEvent('handleAudioSongChanged', null)
            console.warn("playIndex: invalid playlist index " + index)
        }
    }

    togglePlayPause() {
        if (this.impl.isPlaying()) {
            this.impl.pause()
        } else {
            this.impl.play()
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
        return this.impl.currentTime();
    }

    setCurrentTime(time) {
        // TODO: document units
        return this.impl.setCurrentTime(time);
    }

    duration() {
        return this.impl.duration();
    }

    setVolume(volume) {

        return this.impl.setVolume(volume);
    }

    isPlaying() {
        return this.impl.isPlaying();
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

    }

    disconnectView(elem) {

        this.connected_elements = this.connected_elements.filter(e => e!==elem)
    }

    // todo: this 'signal and slot' mechanism is better than the previous impl
    _sendEvent(eventname, event) {
        this.connected_elements = this.connected_elements.filter(e => e.isMounted())

        this.connected_elements.forEach(e => {
            if (e && e[eventname]) {
                e[eventname](event);
            }
        })
    }

}

AudioDevice.instance = function() {

    if (device_instance === null) {

        device_instance = new AudioDevice()

        let impl;
        if (daedalus.platform.isAndroid) {
            impl = new NativeDeviceImpl(device_instance)
        } else {
            impl = new RemoteDeviceImpl(device_instance)
        }

        device_instance.setImpl(impl)

    }

    return device_instance;
}