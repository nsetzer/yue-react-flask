import { combineReducers } from 'redux';
import { routerReducer } from 'react-router-redux';
import auth from './auth';
import message from './message';

const rootReducer = combineReducers({
    routing: routerReducer,
    /* your reducers */
    auth,
    message,
});

export default rootReducer;
