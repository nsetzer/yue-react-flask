
import { createReducer } from '../utils/misc';

import {
    setBodyColor,
    getDefaultTheme,
    createThemeFromPaletteBase,
} from '../utils/theme'

import {
    THEME_SET
} from '../constants/index'

const initialState = {
    theme: getDefaultTheme(),
}

export default createReducer(initialState, {

    [THEME_SET]: (state, payload) =>
        Object.assign({}, state, {
            theme: payload
        }),

});
