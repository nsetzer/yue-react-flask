
import {
    THEME_SET
} from '../constants/index'

function dispatchTheme(theme) {
    return {
        type: THEME_SET,
        payload: theme
    }
}
export function setTheme(theme) {
    return function (dispatch) {
        return dispatch(dispatchTheme(theme))
    }
}

/*
export function setPalette(palette) {
    let theme = createMuiTheme({
        'palette': palette
    });
    return dispatch(dispatchTheme(theme))
}
*/
