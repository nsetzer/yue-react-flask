
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
} from '../constants/index'

const initialState = {
    statusText: null,
    songs: [],
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

});
