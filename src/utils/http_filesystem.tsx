
let request = require('request-promise');

import env from '../env'

/*
list a directory or download a file
*/
export function filesystem_get_path(token: string, root: string, path: string) {
    let url: string = env.baseUrl + '/api/fs/${root}/path/${path}'

    let options = {
        method: 'GET',
        uri: url,
        headers: {
            'Authorization': token,
        },
        json: true,
    };

    return request(options);
}
