
var request = require('request-promise');

import env from '../env'



export function user_queue_get(token : string) {
    let url : string = env.baseUrl + '/api/queue'

    var options = {
        method: 'GET',
        uri: url,
        headers: {
            'Authorization': token,
        },
        json: true,
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
        json: true,
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
    };

    return request(options);
}