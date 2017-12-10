import * as React from 'react';

import { Router, Route, Switch } from 'react-router-dom';

import App from './components/App';
import LoginView from './components/LoginView';
import AboutView from './components/AboutView';
import MainView from './components/MainView';
import RegisterView from './components/RegisterView';
import TestView from './components/TestView';
import RandomInt from './components/RandomInt';
import TestMessage from './components/TestMessage';
import NotFoundView from './components/NotFoundView';

import { requireAuthentication } from './components/auth/AuthenticatedComponent';
import { requireNoAuthentication } from './components/auth/NotAuthenticatedComponent';
import { DetermineAuth } from './components/auth/DetermineAuth';

import History from "./history"

//https://github.com/reactjs/react-router-tutorial/tree/master/lessons/06-params

//
class AppRouter extends React.Component {

  render() {
  return (
    <Router history={History}>
      <Switch>
      <Route exact path="/" component={App} />
      <Route exact path="/test" component={requireNoAuthentication(TestView)} />
      <Route exact path="/login" component={requireNoAuthentication(LoginView)} />
      <Route exact path="/register" component={requireNoAuthentication(RegisterView)} />
      <Route path="/main" component={requireAuthentication(MainView)}/>
      <Route exact path="/about/:topic" component={AboutView} />
      <Route component={DetermineAuth(NotFoundView)} />
      </Switch>
    </Router>
  )}

}
export default AppRouter;