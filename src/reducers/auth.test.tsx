
import { expect } from 'chai';

import * as authReducer from "./auth"

import {
    LOGIN_USER_SUCCESS,
    LOGIN_USER_FAILURE,
    LOGIN_USER_REQUEST,
    LOGOUT_USER,
    REGISTER_USER_FAILURE,
    REGISTER_USER_REQUEST,
    REGISTER_USER_SUCCESS,
} from '../constants/index';

it('should initiate the login state', () => {

    const action = {
        type: LOGIN_USER_REQUEST,
        payload: {}
    };

    const finalState = authReducer.default(authReducer.initialState, action);

    expect(finalState.isAuthenticating).to.be.true;
    expect(finalState.statusText).to.be.null;

});