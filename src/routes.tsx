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

// https://github.com/reactjs/react-router-tutorial/tree/master/lessons/06-params

class AppRouter extends React.Component {

  public render() {
  return (
    <Router history={History}>
      <Switch>
      <Route exact path="/" component={App} />
      <Route exact path="/login" component={requireNoAuthentication(LoginView)} />
      <Route exact path="/register" component={requireNoAuthentication(RegisterView)} />
      <Route path="/main" component={requireAuthentication(MainView)}/>
      <Route component={DetermineAuth(NotFoundView)} />
      </Switch>
    </Router>
  )}

}

export default AppRouter;


