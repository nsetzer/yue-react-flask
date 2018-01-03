/* eslint camelcase: 0 */

import axios from 'axios';
const request = require('request-promise');

import env from '../env'

// TODO: remove axios
// https://github.com/request/request-promise

const tokenConfig = (token) => ({
    headers: {
        'Authorization': token, // eslint-disable-line quote-props
    },
});

export function validate_token(token) {
    let url = env.baseUrl + '/api/user/token'
    let body = { token, }
    let config = { withCredentials: true }
    return axios.post(url, body, config );
}

export function create_user(email, password) {
    return axios.post(env.baseUrl + '/api/user', {
        email,
        password,
    });
}

export  function change_user_password(token: string, password) {
    let url: string = env.baseUrl + '/api/user/password'

    let options = {
        method: 'PUT',
        uri: url,
        body: {password: password},
        headers: {
            'Authorization': token,
        },
        json: true,
    };

    return request(options);
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


