


import 'raf/polyfill';


import { expect, assert } from 'chai';

import * as authActions from "./auth"

import {
    LOGIN_USER_SUCCESS,
    LOGIN_USER_FAILURE,
    LOGIN_USER_REQUEST,
    LOGOUT_USER,
    REGISTER_USER_FAILURE,
    REGISTER_USER_REQUEST,
    REGISTER_USER_SUCCESS,
} from '../constants/index';

// mock local storage
let current_token = ""
window.localStorage = {
    removeItem: (token) => {current_token=""},
    setItem: (token, value) => {current_token = value},
}

it('should login the user, then out', async function() {

    let email = "user000"
    let password = "user000"

    let states = []
    function dispatch(state) {
        states.push(state)
        return state
    }

    // result is set to the final dispatched value
    let result = await authActions.loginUser(email, password, "/main")(dispatch);

    expect(result.type).to.eq(LOGIN_USER_SUCCESS)
    //assert.typeOf(result.payload.token, 'string')

    // states will contain all dispatched states.
    expect(states[0].type).to.eq(LOGIN_USER_REQUEST)
    expect(states[1].type).to.eq(LOGIN_USER_SUCCESS)

    result = await authActions.logoutAndRedirect()(dispatch);
    expect(result.type).to.eq(LOGOUT_USER)
});
