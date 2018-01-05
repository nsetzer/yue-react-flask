
import { createReducer } from '../utils/misc';

import {
    FILESYSTEM_REQUEST,
    FILESYSTEM_GET_PATH,
    FILESYSTEM_FAILURE,
} from '../constants/index'

const initialState = {
    statusText: null,
    directories: [],
    files: [],
    name: "",
    parent_directory: "",
    current_directory: "",
}

export default createReducer(initialState, {
    [FILESYSTEM_REQUEST]: (state) =>
        Object.assign({}, state, {
            statusText: "make request",
        }),
    [FILESYSTEM_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            statusText: payload.status + ": " + payload.statusText
        }),
    [FILESYSTEM_GET_PATH]: (state, payload) => {

        return Object.assign({}, state, {
            statusText: null,
            directories: payload.result.directories,
            files: payload.result.files,
            name: payload.result.name,
            parent_directory: payload.result.parent,
            current_directory: payload.result.path,
        })
    },
});
