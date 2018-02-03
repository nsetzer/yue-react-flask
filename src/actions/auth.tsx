import { BrowserRouter } from 'react-router-dom';

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

import { parseJSON } from '../utils/misc';
import {
    get_token,
    create_user,
    change_user_password,
    data_about_user
} from '../utils/http_functions';

import History from '../history'

export function setUserInformation( info ) {
    return {
        type: SET_USER_INFORMATION,
        payload: {
            info,
        },
    };
}

export function loginUserSuccess(token) {
    localStorage.setItem('token', token);
    return {
        type: LOGIN_USER_SUCCESS,
        payload: {
            token,
        },
    };
}

export function loginUserFailure(error) {
    localStorage.removeItem('token');
    return {
        type: LOGIN_USER_FAILURE,
        payload: {
            status: error.response.status,
            statusText: error.response.statusText,
        },
    };
}

export function loginUserRequest() {
    return {
        type: LOGIN_USER_REQUEST,
    };
}

export function logout() {
    localStorage.removeItem('token');
    return {
        type: LOGOUT_USER,
    };
}

export function logoutAndRedirect() {
    return (dispatch) => {
        History.push('/');
        return dispatch(logout());
    };
}
/*
export function redirectToRoute(route) {
    return () => {
        BrowserRouter.push(route);
    };
}
*/
export function loginUser(email, password, target) {
    return function (dispatch) {
        dispatch(loginUserRequest());
        return get_token(email, password)
            .then(parseJSON)
            .then(response => {
                try {
                    History.push(target);
                    return dispatch(loginUserSuccess(response.token));
                } catch (e) {
                    dispatch(loginUserFailure({
                        response: {
                            status: 403,
                            statusText: 'Invalid token',
                        },
                    }));
                }
            })
            .catch(error => {
                console.log(error)
                dispatch(loginUserFailure({
                    response: {
                        status: 403,
                        statusText: 'Invalid username or password',
                    },
                }));
            });
    };
}

export function getUserInformation(token) {

    console.log("getUserInformation")
    return function (dispatch) {
        //let token = localStorage.getItem('token');
        console.log("getUserInformation: " + token)
        return data_about_user(token)
            .then(res => {
                console.log("got here")
                console.log(res)
                return dispatch(setUserInformation(res.result));
            })
            .catch(error => {
                console.log("got error")
                console.log(error.message)
                return dispatch(setUserInformation(null));
            });
    };
}

export function registerUserRequest() {
    return {
        type: REGISTER_USER_REQUEST,
    };
}

export function registerUserSuccess(token) {
    localStorage.setItem('token', token);
    return {
        type: REGISTER_USER_SUCCESS,
        payload: {
            token,
        },
    };
}

export function registerUserFailure(error) {
    localStorage.removeItem('token');
    return {
        type: REGISTER_USER_FAILURE,
        payload: {
            status: error.response.status,
            statusText: error.response.statusText,
        },
    };
}

export function registerUser(email, password, target) {
    return function (dispatch) {
        dispatch(registerUserRequest());
        return create_user(email, password)
            .then(parseJSON)
            .then(response => {
                try {
                    dispatch(registerUserSuccess(response.token));
                    History.push(target);
                } catch (e) {
                    dispatch(registerUserFailure({
                        response: {
                            status: 403,
                            statusText: 'Invalid token',
                        },
                    }));
                }
            })
            .catch(error => {
                dispatch(registerUserFailure({
                    response: {
                        status: 403,
                        statusText: 'User with that email already exists',
                    },
                }
                ));
            });
    };
}

export function changePasswordRequest() {
    return {
        type: CHANGE_PASSWORD_REQUEST,
    };
}

export function changePasswordSuccess() {
    return {
        type: CHANGE_PASSWORD_SUCCESS,
        payload: {},
    };
}

export function changePasswordFailure(error) {
    localStorage.removeItem('token');
    return {
        type: CHANGE_PASSWORD_FAILURE,
        payload: {
            status: error.response.status,
            statusText: error.response.statusText,
        },
    };
}

export function changePassword(password, target) {
    return function (dispatch) {
        dispatch(changePasswordRequest());
        let token = localStorage.getItem('token');
        return change_user_password(token, password)
            .then(parseJSON)
            .then(response => {
                try {
                    dispatch(changePasswordSuccess());
                    History.push(target);
                } catch (e) {
                    console.error(e)
                    dispatch(changePasswordFailure({
                        response: {
                            status: 403,
                            statusText: 'Invalid token',
                        },
                    }));
                }
            })
            .catch(error => {
                console.error(error)
                dispatch(changePasswordFailure({
                    response: {
                        status: 403,
                        statusText: 'User does not exist', // what?
                    },
                }
                ));
            });
    };
}
