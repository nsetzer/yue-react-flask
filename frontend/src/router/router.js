from module daedalus import { AuthenticatedRouter, patternCompile }

import module api

let current_match = null;

export class AppRouter extends AuthenticatedRouter {

    isAuthenticated() {
        return api.getUsertoken() !== null
    }

    setMatch(match) {
        current_match = match;
    }
}

AppRouter.match = () => {
    return current_match;
}

export function navigate(location) {
    history.pushState({}, "", location)
}

export const route_urls = {
    userStoragePreview: "/u/storage/preview/:path*",
    userStorageList: "/u/storage/list/:path*",
    userStorage: "/u/storage/:mode/:path*",
    userFs: "/u/fs/:path*",
    userPlaylist: "/u/playlist",
    userSettings: "/u/settings",
    userLibraryList: "/u/library/list",
    userLibrarySync: "/u/library/sync",
    userLibrarySavedSearch: "/u/library/saved",
    userRadio: "/u/radio",
    userWildCard: "/u/:path*",
    login: "/login",
    publicFile: "/p/:uid/:filename",
    wildCard: "/:path*",
}

// construct an object with the same properties as route_urls
// which map to functions which build valid urls
export const routes = {};
Object.keys(route_urls).map(key => {
    routes[key] = patternCompile(route_urls[key])
})
