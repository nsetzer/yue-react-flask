import { createReducer } from '../utils/misc';

import {
    TEST_MESSSAGE_CREATE,
    TEST_MESSSAGE_DELETE,
    TEST_MESSSAGE_GET_ALL,
    TEST_MESSSAGE_SUCCESS,
    TEST_MESSSAGE_FAILURE,
    TEST_RANDOM_INT,
} from '../constants/index';

const initialState = {
    currentInteger: 0,
    statusText: null,
    messages: [],
}

export default createReducer(initialState, {
    [TEST_RANDOM_INT]: (state, payload) =>
        Object.assign({}, state, {
            statusText: null,
            currentInteger: payload.value,
        }),
    [TEST_MESSSAGE_CREATE]: (state) =>
        Object.assign({}, state, {
            statusText: null,
        }),
    [TEST_MESSSAGE_DELETE]: (state) =>
        Object.assign({}, state, {
            statusText: null,
        }),
    [TEST_MESSSAGE_GET_ALL]: (state) =>
        Object.assign({}, state, {
            statusText: null,
        }),
    [TEST_MESSSAGE_SUCCESS]: (state, payload) =>
        Object.assign({}, state, {
            statusText: null,
            messages: payload.messages
        }),
    [TEST_MESSSAGE_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            statusText: `Authentication Error: ${payload.status} ${payload.statusText}`
        }),

});
