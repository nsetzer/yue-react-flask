

import module daedalus
import module api.requests

//include './util.js'
include './token.js'

export const env = {
    //`http://${window.location.hostname}:4200`
    // baseUrl is empty when running in production
    // for development set to the full qualified url of the backend
    baseUrl: (daedalus.env && daedalus.env.baseUrl)?daedalus.env.baseUrl:""
}

//console.log(`base url: ${env.baseUrl}`)
env.origin = window.location.origin

// returns {token: token}
export function authenticate(email, password) {
    const url = env.baseUrl + '/api/user/login';
    return api.requests.post_json(url, {email, password});
}

// returns {reason, token_is_valid}
export function validate_token(token) {
    const url = env.baseUrl + '/api/user/token';
    return api.requests.post_json(url, {token});
}

export function fsGetRoots() {
    const url = env.baseUrl + '/api/fs/roots';
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

export function fsPathPreviewUrl(root, path) {
    const url = env.baseUrl + daedalus.util.joinpath('/api/fs', root, 'path', path);
    const params = daedalus.util.serializeParameters({
        preview:'thumb',
        'dl': 0,
        'token': getAuthToken(),
    })
    return url + params
}

export function fsPathUrl(root, path, dl) {

    const url = env.baseUrl + daedalus.util.joinpath('/api/fs', root, 'path', path);
    const params = daedalus.util.serializeParameters({
        'dl': dl,
        'token': getAuthToken(),
    })
    return url + params
}

export function fsGetPath(root, path) {
    const url = env.baseUrl + daedalus.util.joinpath('/api/fs', root, 'path', path);
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

export function fsGetPathContent(root, path) {
    const url = env.baseUrl + daedalus.util.joinpath('/api/fs', root, 'path', path);
    const cfg = getAuthConfig()
    return api.requests.get_text(url, cfg);
}

export function fsGetPathContentUrl(root, path) {

    const url = env.origin + daedalus.util.joinpath('/u/storage/preview', root, path);
    return url;
}

export function fsGetPublicPathUrl(uid, name) {

    const url = env.baseUrl + daedalus.util.joinpath('/api/fs/public', uid, name);
    return url;
}

export function fsSearch(root, path, terms, page, limit) {
    const params = daedalus.util.serializeParameters({path, terms, page, limit})
    const url = env.baseUrl + '/api/fs/' + root +'/search' + params;
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

export function fsPublicUriGenerate(root, path) {
    const url = env.baseUrl + '/api/fs/public/' + root +'/path/' + path
    const cfg = getAuthConfig()
    return api.requests.put_json(url, {}, cfg);
}

export function fsPublicUriRevoke(root, path) {
    const params = daedalus.util.serializeParameters({revoke:true})
    const url = env.baseUrl + '/api/fs/public/' + root +'/path/' + path + params
    const cfg = getAuthConfig()
    return api.requests.put_json(url, {}, cfg);
}

export function fsPublicUriInfo(uid, name) {
    const params = daedalus.util.serializeParameters({info:true})
    const url = env.baseUrl + daedalus.util.joinpath('/api/fs/public', uid, name) + params
    return api.requests.get_json(url);
}

export function fsNoteList(root, base) {
    const params = daedalus.util.serializeParameters({root, base})
    const url = env.baseUrl + '/api/fs/notes' + params;
    const cfg = getAuthConfig()
    cfg.headers['Content-Type'] = "application/json"
    return api.requests.get_json(url, cfg);
}

export function fsNoteCreate(root, base, title, content, crypt, password) {
    const params = daedalus.util.serializeParameters({root, base, title, crypt})
    const url = env.baseUrl + '/api/fs/notes' + params;
    const cfg = getAuthConfig()
    cfg.headers['X-YUE-PASSWORD'] = password
    return api.requests.post(url, content, cfg);
}

export function fsNoteGetContent(root, base, note_id, crypt, password) {
    const params = daedalus.util.serializeParameters({root, base, crypt})
    const url = env.baseUrl + '/api/fs/notes/' + note_id + params;
    const cfg = getAuthConfig()
    cfg.headers['X-YUE-PASSWORD'] = password
    return api.requests.get_text(url, cfg);
}

export function fsNoteSetContent(root, base, note_id, content, crypt, password) {
    const params = daedalus.util.serializeParameters({root, base, crypt})
    const url = env.baseUrl + '/api/fs/notes/' + note_id + params;
    const cfg = getAuthConfig()
    cfg.headers['X-YUE-PASSWORD'] = password
    cfg.headers['Content-Type'] = 'text/plain'
    return api.requests.post(url, content, cfg);
}

export function queueGetQueue() {
    const url = env.baseUrl + '/api/queue';
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

export function queueSetQueue(songList) {
    const url = env.baseUrl + '/api/queue';
    const cfg = getAuthConfig()
    return api.requests.post_json(url, songList, cfg);
}

export function queuePopulate() {
    const url = env.baseUrl + '/api/queue/populate';
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

export function queueCreate(query, limit=50) {
    const params = daedalus.util.serializeParameters({query, limit})
    const url = env.baseUrl + '/api/queue/create' + params;
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

export function librarySongAudioUrl(songId) {
    const url = env.baseUrl + `/api/library/${songId}/audio`;
    const params = daedalus.util.serializeParameters({
        'token': getAuthToken(),
    })
    return url + params
}

export function librarySearchForest(query, showBanished=false) {
    const params = daedalus.util.serializeParameters({query, showBanished})
    const url = env.baseUrl + '/api/library/forest' + params;
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

export function librarySong(songId) {
    const url = env.baseUrl + '/api/library/' + songId;
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

export function libraryDomainInfo() {
    const url = env.baseUrl + '/api/library/info';
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}


export function userDoc(hostname) {
    const params = daedalus.util.serializeParameters({hostname})
    const url = env.baseUrl + '/api/doc' + params;
    const cfg = getAuthConfig()
    return api.requests.get_text(url, cfg);
}

export function radioVideoInfo(videoId) {
    const params = daedalus.util.serializeParameters({videoId})
    const url = env.baseUrl + '/api/radio/video/info' + params;
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

/**
 * params:
 *   crypt: One of: client, server, system, none. default: none
 *          client and system are not supported
 *
 *          none: no encryption is performed
 *          client: file is encrypted, key is managed by the user client side
 *            files are encrypted and decrypted by the client
 *            files can only be decrypted by the owner
 *            the server (and database) never have access to the decrypted key
 *          server: file is encrypted, key is managed by the user server side
 *            files are encrypted and decrypted by the server
 *            files can only be decrypted by the owner
 *            man in the middle attacks could determine the encryption key
 *          system: file is encrypted, key is managed by the application
 *            files are encrypted and decrypted by the server
 *            files can be decrypted by users other than the file owner
 *            the encryption key is compromised if the database is compromised
 */
export function fsUploadFile(root, path, headers, params, success=null, failure=null, progress=null) {

    const urlbase = env.baseUrl + daedalus.util.joinpath('/api/fs', root, 'path', path)
    const cfg = getAuthConfig()
    return daedalus.uploadFile(
        urlbase,
        headers={...cfg.headers, ...headers},
        params=params,
        success,
        failure,
        progress
    );

}