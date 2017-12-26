
import {
    THEME_SET
} from '../constants/index'

import {
    createThemeFromPaletteBase
} from '../utils/theme'

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

export function setPalette(base) {
    return function (dispatch) {

        let theme = createThemeFromPaletteBase(base)
        console.log(base)
        console.log(theme.palette.type)
        return dispatch(dispatchTheme(theme))
    }
}
