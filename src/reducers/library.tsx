
import { createReducer } from '../utils/misc';

import {
    LIBRARY_REQUEST,
    LIBRARY_FAILURE,
    LIBRARY_SEARCH,
    LIBRARY_DOMAIN_INFO,
} from '../constants/index'


const initialState = {
    statusText: null,
    search_results: [],
    search_result_page: 0,
    search_result_page_size: 0,
    domain_artists: [],
    domain_genres: [],
    domain_song_count: 0,
}

export default createReducer(initialState, {
    [LIBRARY_REQUEST]: (state) =>
        Object.assign({}, state, {
            statusText: "make request",
        }),
    [LIBRARY_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            statusText: payload.status + ": " + payload.statusText
        }),
    [LIBRARY_SEARCH]: (state, payload) => {

        return Object.assign({}, state, {
            statusText: "success",
            search_results: payload.result,
            search_result_page: payload.page,
            search_result_page_size: payload.page_index,
        })
    },
    [LIBRARY_DOMAIN_INFO]: (state, payload) => {
        console.log(LIBRARY_DOMAIN_INFO)
        console.log(payload)
        return Object.assign({}, state, {
            statusText: `result length ${payload.num_songs} ${payload.artists.length}`,
            domain_artists: payload.artists,
            domain_genres: payload.genres,
            domain_song_count: payload.num_songs,
        })
    },
});
