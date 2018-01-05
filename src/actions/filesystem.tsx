import {
    FILESYSTEM_REQUEST,
    FILESYSTEM_GET_PATH,
    FILESYSTEM_FAILURE,
} from '../constants/index'

import { filesystem_get_path,
} from "../utils/http_filesystem"

export function filesystemRequest() {
    return {type: FILESYSTEM_REQUEST}
}

export function filesystemListSuccess(payload) {
    return {
        type: FILESYSTEM_GET_PATH,
        payload: payload,
    };
}

export function filesystemListError(error) {
    return {
        type: FILESYSTEM_FAILURE,
        payload: {
            status: error.statusCode,
            statusText: error.toString(),
        },
    };
}

export function filesystemGetPath(root: string, path: string) {
    return function (dispatch) {
        dispatch(filesystemRequest());
        let token = localStorage.getItem('token');
        return filesystem_get_path(token, root, path)
            .then(response => {
                dispatch(filesystemListSuccess(response));
            })
            .catch(error => {
                dispatch(filesystemListError(error));
            })
    }
}
