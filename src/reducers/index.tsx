import { combineReducers } from 'redux';
import { routerReducer } from 'react-router-redux';
import auth from './auth';
import message from './message';
import queue from './queue';

const rootReducer = combineReducers({
    routing: routerReducer,
    /* your reducers */
    auth,
    message,
    queue,
});

export default rootReducer;
