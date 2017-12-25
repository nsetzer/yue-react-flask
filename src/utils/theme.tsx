import createMuiTheme from 'material-ui/styles/createMuiTheme'
import createPalette, { Palette } from 'material-ui/styles/createPalette'
import * as Colors from 'material-ui/colors';
import { fade, lighten, darken } from 'material-ui/styles/colorManipulator'
import { Color } from 'material-ui'

export function makeColor(base,contrast) {
  let color: Color = {
    50:  lighten(base, 1.00),
    100: lighten(base, 0.80),
    200: lighten(base, 0.60),
    300: lighten(base, 0.40),
    400: lighten(base, 0.20),
    500: base,
    600: darken(base, 0.25),
    700: darken(base, 0.50),
    800: darken(base, 0.75),
    900: darken(base, 1.00),
    A100: base,
    A200: base,
    A400: base,
    A700: base,
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
