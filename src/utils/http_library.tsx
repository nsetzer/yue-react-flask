var request = require('request-promise');
var zlib = require('zlib');

import env from '../env'

export function user_library_search(token : string, searchTerm: string) {
    let url : string = env.baseUrl + '/api/library'

    var options = {
        method: 'GET',
        uri: url,
        qs: {
            text: searchTerm,
        },
        headers: {
            'Authorization': token,
        },
        json: true,
    };

    return request(options);
}

export function user_library_domain_info(token : string) {
    let url : string = env.baseUrl + '/api/library/info'

    var options = {
        method: 'GET',
        uri: url,
        headers: {
            'Authorization': token,
        },
        /*gzip: true,*/
        json: true
    };

    return request(options)/*.then( response => {
        console.log(response)
        return JSON.parse(response)
    })*/
}