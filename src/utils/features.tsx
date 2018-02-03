
import store from '../store/configureStore';


function userHasFeature(feat : string): boolean {

    let state = store.getState() as {auth:any};

    console.log(state)
    if (!('auth' in state) || !state.auth) {
        return false;
    }

    let user = state.auth.currentUser;
    if (!(user) || user.features.length==0) {
        return false;
    }

    return user.features.includes(feat)
}

export function readFilesystem() : boolean {
    return userHasFeature("read_filesystem");
}

