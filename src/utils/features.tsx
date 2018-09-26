
import store from '../store/configureStore';

export function getTheme() {
    let state = store.getState() as {theme:any};

    if (!('theme' in state) || !state.theme) {
        return false;
    }

    return state.theme
}

function userHasFeature(feat : string): boolean {

    let state = store.getState() as {auth:any};

    if (!('auth' in state) || !state.auth) {
        return false;
    }


    let user = state.auth.currentUser;
    if (!(user) || user.features.length==0) {
        return false;
    }

    console.log(user.features)

    // <!-- { readFilesystem()? <> : null }
    return true // user.features.includes(feat)
}

export function readFilesystem() : boolean {
    return userHasFeature("filesystem_read");
}

