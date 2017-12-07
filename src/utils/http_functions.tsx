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

export function user_queue_get(token : string) {
    let url : string = env.baseUrl + '/api/queue'

    var options = {
        method: 'GET',
        uri: url,
        headers: {
            'Authorization': token,
        },
        json: true
    };

    return request(options);
}

export function user_queue_populate(token : string) {
    let url : string = env.baseUrl + '/api/queue/populate'

    var options = {
        method: 'GET',
        uri: url,
        headers: {
            'Authorization': token,
        },
        json: true
    };

    return request(options);
}

export function user_queue_set(token : string, song_ids: Array<string>) {
    let url : string = env.baseUrl + '/api/queue'

    var options = {
        method: 'POST',
        uri: url,
        body: song_ids,
        json: true, // Automatically stringifies the body to JSON
        headers: {
            'Authorization': token,
            'Content-Type': 'application/json',
        },
        json: true
    };

    return request(options);
}
