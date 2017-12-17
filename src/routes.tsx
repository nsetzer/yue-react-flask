import * as React from 'react';

import { Router, Route, Switch } from 'react-router-dom';

import App from './components/App';
import LoginView from './components/LoginView';
import MainView from './components/MainView';
import RegisterView from './components/RegisterView';
import NotFoundView from './components/NotFoundView';

import { requireAuthentication } from './components/auth/AuthenticatedComponent';
import { requireNoAuthentication } from './components/auth/NotAuthenticatedComponent';
import { DetermineAuth } from './components/auth/DetermineAuth';

import MuiThemeProvider from 'material-ui/styles/MuiThemeProvider';
import createMuiTheme from 'material-ui/styles/createMuiTheme'
import createPalette, { Palette } from 'material-ui/styles/createPalette'
import * as Color from 'material-ui/colors';
import { fade } from 'material-ui/styles/colorManipulator'

import History from './history'

function getTheme() {
  let palette: Palette = createPalette({
        'type': 'light',
        'primary': Color.blue
        /*'secondary': Colors.green800,*/
    });
  return createMuiTheme({
    'palette': palette
  });
};

const theme = getTheme();

console.log(theme)
// https://github.com/reactjs/react-router-tutorial/tree/master/lessons/06-params

class AppRouter extends React.Component {

  public render() {
  return (
    <MuiThemeProvider theme={theme}>
      <Router history={History}>
        <Switch>
        <Route exact path="/" component={App} />
        <Route exact path="/login" component={requireNoAuthentication(LoginView)} />
        <Route exact path="/register" component={requireNoAuthentication(RegisterView)} />
        <Route path="/main" component={requireAuthentication(MainView)}/>
        <Route component={DetermineAuth(NotFoundView)} />
        </Switch>
      </Router>
    </MuiThemeProvider>
  )}

}

export default AppRouter;
