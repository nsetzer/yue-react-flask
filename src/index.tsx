import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider } from 'react-redux';

import './index.css';

// https://github.com/Lemoncode/redux-by-sample

import registerServiceWorker from './utils/registerServiceWorker';

//import getMuiTheme from 'material-ui/styles/getMuiTheme';
//import MuiThemeProvider from 'material-ui/styles/MuiThemeProvider'
//import darkBaseTheme from 'material-ui/styles/baseThemes/darkBaseTheme';

import AppRouter from "./routes"

import configureStore from './store/configureStore';
const store = configureStore();
      //<MuiThemeProvider muiTheme={getMuiTheme()}>
      //</MuiThemeProvider>

ReactDOM.render((
    <Provider store={store}>
        <AppRouter/>
   </Provider>
), document.getElementById('root'));
registerServiceWorker();
