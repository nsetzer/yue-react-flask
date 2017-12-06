/* eslint camelcase: 0 */

import axios from 'axios';

import env from '../env'


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

export function user_get_queue(token : string) {
    let url : string = env.baseUrl + '/api/queue'
    return axios.get(url, tokenConfig(token))
}

export function user_set_queue(token : string, song_ids: Array<string>) {
    let url : string = env.baseUrl + '/api/queue'
    let headers = {
        'Authorization': token,
        'Content-Type': 'application/json',
    }
    //JSON.stringify(song_ids)
    /*
    return axios.post(url, JSON.stringify(song_ids), {
        headers: headers,
        withCredentials: true,
    })
    */
    /*
    return fetch(url,
    {
        credentials: 'include',
        mode: 'cors',
        headers: {
          'Authorization': token,
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        },
        method: "POST",
        body: JSON.stringify(song_ids)
    })
    */

    /*
    var xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);
    xhr.setRequestHeader('Content-type', 'application/json');
    xhr.setRequestHeader('Authorization', token);
    xhr.onreadystatechange = function () {
        // do something to response
        console.log(xhr);
    };
    xhr.onload = function () {
        // do something to response
        console.log("::" + xhr.responseText);
    };
    xhr.send();
    */
}
