import { combineReducers } from 'redux';
import { routerReducer } from 'react-router-redux';
import auth from './auth';
import message from './message';
import queue from './queue';
import library from './library';
import theme from './theme';

const rootReducer = combineReducers({
    routing: routerReducer,
    /* your reducers */
    auth,
    message,
    queue,
    library,
    theme,
});

export default rootReducer;
