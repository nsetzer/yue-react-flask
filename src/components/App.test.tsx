
import 'raf/polyfill';

import * as React from 'react';
import * as ReactDOM from 'react-dom';

import { Provider } from 'react-redux';
import getMuiTheme from 'material-ui/styles/getMuiTheme';
//import MuiThemeProvider from 'material-ui/styles/MuiThemeProvider'

import AppRouter from "../routes"

import configureStore from '../store/configureStore';
const store = configureStore();


it('renders without crashing', () => {
  const div = document.createElement('div');
  ReactDOM.render(
    <Provider store={store}>
        <AppRouter/>
    </Provider>, div);
});
