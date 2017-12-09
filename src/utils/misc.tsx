/* eslint max-len: 0, no-param-reassign: 0 */
import env from '../env'

export function createConstants(...constants) {
    return constants.reduce((acc, constant) => {
        acc[constant] = constant;
        return acc;
    }, {});
}

export function createReducer(initialState, reducerMap) {
    return (state = initialState, action) => {
        const reducer = reducerMap[action.type];


        return reducer
            ? reducer(state, action.payload)
            : state;
    };
}


export function parseJSON(response) {
    return response.data;
}

export function validateEmail(email) {
    const re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(email);
}

export function fmtDuration(s) {
  var h = Math.floor(s / 3600)
  s %= 3600;
  var m = ("0" + Math.floor(s / 60)).substr(-2)
  s = ("0" + (s % 60)).substr(-2)
  if (h>0) {
    m = ("0" + h).substr(-2) + ":" + m
  }
  return m + ":" + s;
}

export function getSongAudioUrl(song) {
    // in the future, the url may be on a different server
    var params = "?user=" + song.user_id +"&domain=" + song.domain_id
    return env.baseUrl + "/api/library/" + song.id + "/audio" + params
}

export function getSongArtUrl(song) {
    return env.baseUrl + "/api/library/" + song.id + "/art"
}

export function getSongDisplayTitle(song) {
    return song.artist + " - " + song.title;
}