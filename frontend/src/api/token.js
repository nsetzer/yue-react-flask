

let user_token = null
export function getUsertoken() {
    if (user_token === null) {
        const token = window.localStorage.getItem("user_token")
        if (!!token) {
            user_token = token
        }
    }
    return user_token;
}

export function setUsertoken(token) {
    window.localStorage.setItem("user_token", token)
    // cookies can only be used in production (no cross origin requests)
    //
    //const escaped_token = token.replace(/-/g, '%2d').replace(/\./g, '%2e')
    //document.cookie = `user_token=${escaped_token}; path=/; SameSite=Strict; Secure;`
    user_token = token;
}

export function clearUserToken(creds) {
    window.localStorage.removeItem("user_token")
    user_token = null;
}

export function getAuthConfig() {
    return {credentials: 'include', headers: {Authorization: user_token}}
}

export function getAuthToken() {
    return user_token
}
