import * as jwtDecode from 'jwt-decode';

import { createReducer } from '../utils/misc';

import {
    LOGIN_USER_SUCCESS,
    LOGIN_USER_FAILURE,
    LOGIN_USER_REQUEST,
    LOGOUT_USER,
    REGISTER_USER_FAILURE,
    REGISTER_USER_REQUEST,
    REGISTER_USER_SUCCESS,
    CHANGE_PASSWORD_FAILURE,
    CHANGE_PASSWORD_REQUEST,
    CHANGE_PASSWORD_SUCCESS,
    SET_USER_INFORMATION,
} from '../constants/index';

export const initialState = {
    token: null,
    userName: null,
    currentUser: null,
    isAuthenticated: false,
    isAuthenticating: false,
    statusText: null,
    isRegistering: false,
    isRegistered: false,
    registerStatusText: null,
    changePasswordStatusText: null,
};

export default createReducer(initialState, {
    [SET_USER_INFORMATION]: (state, payload) =>
        Object.assign({}, state, {
            currentUser: payload.info,
        }),
    [LOGIN_USER_REQUEST]: (state) =>
        Object.assign({}, state, {
            isAuthenticating: true,
            statusText: null,
        }),
    [LOGIN_USER_SUCCESS]: (state, payload) => {
        let user = jwtDecode(payload.token) as {email:string}
        return Object.assign({}, state, {
            isAuthenticating: false,
            isAuthenticated: true,
            token: payload.token,
            userName: user.email,
            statusText: 'You have been successfully logged in.',
        })},
    [LOGIN_USER_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            isAuthenticating: false,
            isAuthenticated: false,
            token: null,
            userName: null,
            statusText: `Authentication Error: ${payload.status} ${payload.statusText}`,
        }),
    [LOGOUT_USER]: (state) =>
        Object.assign({}, state, {
            isAuthenticated: false,
            token: null,
            userName: null,
            statusText: 'You have been successfully logged out.',
        }),
    [REGISTER_USER_SUCCESS]: (state, payload) => {
        let user = jwtDecode(payload.token) as {email:string}
        return Object.assign({}, state, {
            isAuthenticating: false,
            isAuthenticated: true,
            isRegistering: false,
            token: payload.token,
            userName: user.email,
            registerStatusText: 'You have been successfully logged in.',
        })},
    [REGISTER_USER_REQUEST]: (state) =>
        Object.assign({}, state, {
            isRegistering: true,
        }),
    [REGISTER_USER_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            isAuthenticated: false,
            token: null,
            userName: null,
            registerStatusText: `Register Error: ${payload.status} ${payload.statusText}`,
        }),
    [CHANGE_PASSWORD_SUCCESS]: (state, payload) =>
        Object.assign({}, state, {
            changePasswordStatusText: 'Password Successfully changed.',
        }),
    [CHANGE_PASSWORD_REQUEST]: (state) =>
        Object.assign({}, state, {
            changePasswordStatusText: ""
        }),
    [CHANGE_PASSWORD_FAILURE]: (state, payload) =>
        Object.assign({}, state, {
            changePasswordStatusText: `Change Password Error: ${payload.status} ${payload.statusText}`,
        }),
});
