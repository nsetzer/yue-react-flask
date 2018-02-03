import { createStore, applyMiddleware } from 'redux';
import thunkMiddleware from 'redux-thunk';
import rootReducer from '../reducers';

/*
const debugware = [];
if (process.env.NODE_ENV !== 'production') {
    const createLogger = require('redux-logger');

    debugware.push(createLogger({
        collapsed: true,
    }));
}

*/
function configureStore() {
    const store = createStore(
        rootReducer,
        applyMiddleware(thunkMiddleware)
    );

    if (module.hot) {
        // Enable Webpack hot module replacement for reducers
        module.hot.accept('../reducers', () => {
            const nextRootReducer = require('../reducers/index').default;

            store.replaceReducer(nextRootReducer);
        });
    }

    return store;
}

export default configureStore()