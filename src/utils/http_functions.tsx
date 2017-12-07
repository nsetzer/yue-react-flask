/* eslint camelcase: 0 */

import axios from 'axios';
var request = require('request-promise');

import env from '../env'

// TODO: remove axios
// https://github.com/request/request-promise

const tokenConfig = (token) => ({
    headers: {
        'Authorization': token, // eslint-disable-line quote-props
    },
});


export function validate_token(token) {
    var url = env.baseUrl + '/api/user/token'
    var body = { token, }
    var config = { withCredentials: true }
    return axios.post(url, body, config );
}

export function create_user(email, password) {
    return axios.post(env.baseUrl + '/api/user', {
        email,
        password,
    });
}

export function get_token(email, password) {
    return axios.post(env.baseUrl + '/api/user/login', {
        email: email,
        password: password,
    });
}

export function data_about_user(token) {
    return axios.get(env.baseUrl + '/api/user', tokenConfig(token));
}

export function get_random_int() {
    return axios.get(env.baseUrl + '/api/random')
}

export function create_message(text) {
    return axios.post(env.baseUrl + '/api/message',
                      {message:text});
}

export function get_all_messages() {
    return axios.get(env.baseUrl + '/api/message')
}

export function delete_message(id) {
    return axios.delete(env.baseUrl + `/api/message/${id}`)
}


