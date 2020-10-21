

let user_token = null
export function getUsertoken() {
    if (user_token === null) {
        const token = LocalStorage.getItem("user_token")
        if (token && token.length > 0) {
            user_token = token
        }
    }
    return user_token;
}

export function setUsertoken(token) {
    LocalStorage.setItem("user_token", token)
    user_token = token;
}

export function clearUserToken(creds) {
    LocalStorage.removeItem("user_token")
    user_token = null;
}

export function getAuthConfig() {
    return {credentials: 'include', headers: {Authorization: user_token}}
}

export function getAuthToken() {
    return user_token
}