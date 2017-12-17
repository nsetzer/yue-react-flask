import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider } from 'react-redux';

import 'typeface-roboto'

import './index.css';

import registerServiceWorker from './utils/registerServiceWorker';

import AppRouter from './routes'

import configureStore from './store/configureStore';
const store = configureStore();

ReactDOM.render((
    <Provider store={store}>
        <AppRouter/>
    </Provider>
), document.getElementById('root'));
registerServiceWorker();
