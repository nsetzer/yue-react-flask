
import { createReducer } from '../utils/misc';

import {
    QUEUE_GET,
    QUEUE_GET_SUCCESS,
    QUEUE_GET_FAILURE,
    QUEUE_POPULATE,
    QUEUE_POPULATE_SUCCESS,
    QUEUE_POPULATE_FAILURE,
    QUEUE_SET,
    QUEUE_SET_SUCCESS,
    QUEUE_SET_FAILURE,
    QUEUE_NEXT,
    QUEUE_NEXT_SUCCESS,
    QUEUE_NEXT_FAILURE,
    QUEUE_PREVIOUS,
    QUEUE_PREVIOUS_SUCCESS,
    QUEUE_PREVIOUS_FAILURE,
    QUEUE_PLAY_INDEX,
    QUEUE_PLAY_NEXT,
    QUEUE_DELETE_INDEX,
} from '../constants/index'

const initialState = {
    statusText: null,
    songs: [],
    history: [],
}

export default createReducer(initialState, {
    [QUEUE_GET]: (state) =>
        Object.assign({}, state, {
            statusText: null,
        }),
    [QUEUE_GET_SUCCESS]: (state, payload) =>
        Object.assign({}, state, {
            statusText: null,
            songs: payload,
        }),
    [QUEUE_GET_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            statusText: payload.statusText
        }),

    [QUEUE_SET]: (state) =>
        Object.assign({}, state, {
            statusText: null,
        }),
    [QUEUE_SET_SUCCESS]: (state) =>
        Object.assign({}, state, {
            statusText: null,
        }),
    [QUEUE_SET_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            statusText: payload.statusText
        }),

    [QUEUE_POPULATE]: (state) =>
        Object.assign({}, state, {
            statusText: null,
        }),
    [QUEUE_POPULATE_SUCCESS]: (state, payload) =>
        Object.assign({}, state, {
            statusText: null,
            songs: payload,
        }),
    [QUEUE_POPULATE_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            statusText: payload.statusText
        }),

    [QUEUE_NEXT]: (state) =>
        Object.assign({}, state, {
            statusText: null,
        }),
    [QUEUE_NEXT_SUCCESS]: (state, payload) => {
        if (state.songs.length>0) {
            let song = state.songs[0]
            let new_songs = state.songs.slice(1,state.songs.length)
            let new_history = state.history.slice(0,state.history.length)
            new_history.push(song)
            //if (new_history.length>5) {
            //    new_history.splice(-5,5)
            //}
            return Object.assign({}, state, {
                statusText: null,
                songs: new_songs,
                history: new_history,
            })
        } else {
            return Object.assign({}, state, {
                statusText: "no next song",
            })
        }
    },
    [QUEUE_NEXT_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            statusText: payload.statusText
        }),
    [QUEUE_PREVIOUS]: (state) =>
        Object.assign({}, state, {
            statusText: null,
        }),
    [QUEUE_PREVIOUS_SUCCESS]: (state, payload) => {
        if (state.history.length>0) {
            let new_history = state.history.slice(0,state.history.length)
            let new_songs = state.songs.slice(0,state.songs.length)
            let song = new_history.splice(-1,1)[0] // remove last element in list
            new_songs.unshift(song) //prepend element
            return Object.assign({}, state, {
                statusText: null,
                songs: new_songs,
                history: new_history,
            })
        } else {
            return Object.assign({}, state, {
                statusText: "no previous song",
            })
        }
    },
    [QUEUE_PLAY_INDEX]: (state, payload) => {
        let index = payload.index
        if (index < state.songs.length) {

            let new_history = state.history.slice(0,state.history.length)
            new_history.concat(state.songs.slice(0,index))
            let new_songs = state.songs.slice(index,state.songs.length)
            return Object.assign({}, state, {
                    statusText: null,
                    songs: new_songs,
                    history: new_history,
                })
        } else {
            return Object.assign({}, state, {
                statusText: "invalid index",
            })
        }

    },
    [QUEUE_PLAY_NEXT]: (state, payload) => {
        let index = payload.index
        if (index < state.songs.length) {
            let new_songs = state.songs.slice(0,state.songs.length)
            let songs = new_songs.splice(index,1)
            new_songs.splice(1,0,...songs)
            return Object.assign({}, state, {
                    statusText: null,
                    songs: new_songs,
                })
        } else {
            return Object.assign({}, state, {
                statusText: "invalid index",
            })
        }
    },
    [QUEUE_DELETE_INDEX]: (state, payload) => {
        let index = payload.index
        if (index < state.songs.length) {
            let new_songs = state.songs.slice(0,state.songs.length)
            new_songs.splice(index,1)
            return Object.assign({}, state, {
                    statusText: null,
                    songs: new_songs,
                })
        } else {
            return Object.assign({}, state, {
                statusText: "invalid index",
            })
        }
    },
    [QUEUE_PREVIOUS_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            statusText: payload.statusText
        }),


});
