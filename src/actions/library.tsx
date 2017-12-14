
import {
    LIBRARY_REQUEST,
    LIBRARY_FAILURE,
    LIBRARY_SEARCH,
    LIBRARY_DOMAIN_INFO,
} from '../constants/index'

import { user_library_search,
         user_library_domain_info,
    } from "../utils/http_library"


export function libraryRequest() {
    return {type: LIBRARY_REQUEST}
}

export function librarySuccess(payload, successType) {
    return {
        type: successType,
        payload: payload,
        statusText: "success"
    };
}

export function libraryError(error) {
    console.error(error)
    return {
        type: LIBRARY_FAILURE,
        payload: {
            status: error.statusCode,
            statusText: error.toString(),
        },
    };
}

export function librarySearch(term) {
    return function (dispatch) {
        dispatch(libraryRequest());
        var token = localStorage.getItem('token');
        return user_library_search(token, term)
            .then(response => {
                dispatch(librarySuccess(response,
                                      LIBRARY_SEARCH));
            })
            .catch(error => {
                dispatch(libraryError(error));
            })
    }
}

export function libraryGetArtistSongs(artist) {
    // todo, be default there is a limit on search results
    // create a work around for this special case
    return librarySearch(`artist="${artist}"`);
}

export function libraryGetAlbumSongs(artist, album) {
    // todo, be default there is a limit on search results
    // create a work around for this special case
    return librarySearch(`artist="${artist}" && album="${album}"`);
}

export function libraryGetDomainInfo() {
    return function (dispatch) {
        dispatch(libraryRequest());
        var token = localStorage.getItem('token');
        return user_library_domain_info(token)
            .then(response => {
                dispatch(librarySuccess(response.result,
                                        LIBRARY_DOMAIN_INFO));
            })
            .catch(error => {
                dispatch(libraryError(error));
            })
    }
}