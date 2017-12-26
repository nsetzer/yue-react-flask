import createMuiTheme from 'material-ui/styles/createMuiTheme'
import createPalette, { Palette } from 'material-ui/styles/createPalette'
import * as Colors from 'material-ui/colors';
import { fade, lighten, darken } from 'material-ui/styles/colorManipulator'
import { Color } from 'material-ui'

export function makeColor(base,contrast) {
  let color: Color = {
    50:  lighten(base, 0.50),
    100: lighten(base, 0.40),
    200: lighten(base, 0.30),
    300: lighten(base, 0.20),
    400: lighten(base, 0.10),
    500: base,
    600: darken(base, 0.12),
    700: darken(base, 0.25),
    800: darken(base, 0.37),
    900: darken(base, 0.50),
    A100: lighten(base, 0.40),
    A200: lighten(base, 0.30),
    A400: lighten(base, 0.10),
    A700: darken(base, 0.25),
    contrastDefaultColor: contrast
  };
  return color
}

export function setBodyColor(color) {
  document.body.style.backgroundColor = color;
}

export function getDefaultTheme() {
  let palette: Palette = createPalette({
        'type': 'light',
    });
  return createMuiTheme({
    'palette': palette
  });
};

export function createThemeFromPaletteBase(base) {
    let palette: Palette = createPalette(base);
    return createMuiTheme({
        'palette': palette
    });
}
