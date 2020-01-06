

import daedalus
import api.requests

export const env = {
    //`http://${window.location.hostname}:4200`
    // baseUrl is empty when running in production
    // for development set to the full qualified url of the backend
    baseUrl: (daedalus.env && daedalus.env.baseUrl)?daedalus.env.baseUrl:""
}

let user_token = null
export function getUsertoken() {
    if (user_token === null) {
        const token = window.localStorage.getItem("user_token")
        if (token) {
            user_token = token
        }
    }
    return user_token;
}

export function setUsertoken(token) {
    window.localStorage.setItem("user_token", token)
    user_token = token;
}

export function clearUserToken(creds) {
    window.localStorage.removeItem("user_token")
    user_token = null;
}

export function getAuthConfig() {
    return {credentials: 'include', headers: {Authorization: user_token}}
}

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
    const url = env.baseUrl + '/api/fs/' + root +'/path/' + path;
    const params = daedalus.util.serializeParameters({
        preview:'thumb',
        'dl': 0,
        'token': user_token,
    })
    return url + params
}

export function fsGetPath(root, path) {
    const url = env.baseUrl + '/api/fs/' + root +'/path/' + path;
    const cfg = getAuthConfig()
    return api.requests.get_json(url, cfg);
}

export function fsSearch(root, path, terms, page, limit) {
    const params = daedalus.util.serializeParameters({path, terms, page, limit})
    const url = env.baseUrl + '/api/fs/' + root +'/search/' + path + parms;
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

export function fsPublicUriInfo(file_id) {
    const url = env.baseUrl + '/api/fs/public/' + file_id + serialize({info: true})
    return api.requests.get_json(url);
}
