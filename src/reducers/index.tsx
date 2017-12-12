import { combineReducers } from 'redux';
import { routerReducer } from 'react-router-redux';
import auth from './auth';
import message from './message';
import queue from './queue';
import library from './library';

const rootReducer = combineReducers({
    routing: routerReducer,
    /* your reducers */
    auth,
    message,
    queue,
    library,
});

export default rootReducer;
