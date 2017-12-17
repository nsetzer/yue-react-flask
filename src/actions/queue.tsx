
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

import {
    user_queue_get,
    user_queue_populate,
    user_queue_set
} from '../utils/http_queue';


export function queueRequest(queueType) {
    return {type: queueType}
}

// a success type which contains the list of song_ids
// presently in the queue
export function queueSuccess(song_ids, successType) {
    return {
        type: successType,
        payload: song_ids,
    };
}

// a success type with no payload data
export function queueSuccessVoid(successType) {
    return {
        type: successType,
        payload: {},
    };
}

export function queueError(error, errorType) {
    console.error(errorType + " : " +error)
    return {
        type: errorType,
        payload: {
            status: error.statusCode,
            statusText: error.statusText,
        },
    };
}

export function getQueue() {
    return function (dispatch) {
        dispatch(queueRequest(QUEUE_GET));
        var token = localStorage.getItem('token');
        return user_queue_get(token)
            .then(response => {
                dispatch(queueSuccess(response.result,
                                      QUEUE_GET_SUCCESS));
            })
            .catch(error => {
                dispatch(queueError(error,
                                    QUEUE_GET_FAILURE));
            })
    }
}

export function setQueue(song_ids : Array<string>) {
    return function (dispatch) {
        dispatch(queueRequest(QUEUE_SET));
        var token = localStorage.getItem('token');
        return user_queue_set(token, song_ids)
            .then(response => {
                dispatch(queueSuccessVoid(QUEUE_SET_SUCCESS));
            })
            .catch(error => {
                dispatch(queueError(error,
                                    QUEUE_SET_FAILURE));
            })
    }
}

export function populateQueue() {
    return function (dispatch) {
        dispatch(queueRequest(QUEUE_POPULATE));
        var token = localStorage.getItem('token');
        return user_queue_populate(token)
            .then(response => {
                dispatch(queueSuccess(response.result,
                                      QUEUE_POPULATE_SUCCESS));
            })
            .catch(error => {
                dispatch(queueError(error,
                                    QUEUE_POPULATE_FAILURE));
            })
    }
}

export function nextSongInQueue() {
    return function (dispatch) {
        dispatch(queueRequest(QUEUE_NEXT));
        dispatch(queueSuccess(null,
                               QUEUE_NEXT_SUCCESS));
        return null
    }
}

export function previousSongInQueue() {
    return function (dispatch) {
        dispatch(queueRequest(QUEUE_NEXT));

        dispatch(queueSuccess(null,
                              QUEUE_PREVIOUS_SUCCESS));
        return null

    }
}

export function playIndexInQueue(index) {
    return function (dispatch) {
        dispatch(queueSuccess({index: index}, QUEUE_PLAY_INDEX));
        return null;
    }
}

export function playNextInQueue(index) {
    return function (dispatch) {
        dispatch(queueSuccess({index: index}, QUEUE_PLAY_NEXT));
        return null;
    }
}

export function deleteIndexInQueue(index) {
    return function (dispatch) {
        dispatch(queueSuccess({index: index}, QUEUE_DELETE_INDEX));
        return null;
    }
}

