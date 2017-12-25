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

import History from './history'

import { setBodyColor } from './utils/theme'

import * as actionCreators from './actions/theme'
import MuiThemeProvider from 'material-ui/styles/MuiThemeProvider';
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
/*makeColor("#d6780)")*/
/*
function getTheme() {
  let palette: Palette = createPalette({
        'type': 'dark',
        'primary': makeColor("#ff6700", "dark"),
        'secondary': Colors.amber
    });
  return createMuiTheme({
    'palette': palette
  });
};
*/

// https://github.com/reactjs/react-router-tutorial/tree/master/lessons/06-params

export interface IAppRouterProps {
  theme: any,
  children?: any,
  setTheme: (theme) => any,
}

export interface IAppRouterState {

}

class AppRouter extends React.Component<IAppRouterProps, IAppRouterState> {

  public render() {

  let _theme = this.props.theme;
  console.log(_theme)
  setBodyColor(_theme.palette.background.default)
  return (
    <MuiThemeProvider theme={_theme}>
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

function mapStateToProps(state) {
  return {
    theme: state.theme.theme
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(AppRouter);
