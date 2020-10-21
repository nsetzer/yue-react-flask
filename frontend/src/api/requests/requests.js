
export function get_text(url, parameters) {

    if (parameters === undefined) {
        parameters = {}
    }

    parameters.method = "GET"

    return fetch(url, parameters).then((response) => {return response.text()})
}

export function get_json(url, parameters) {

    if (parameters === undefined) {
        parameters = {}
    }

    parameters.method = "GET"

    return fetch(url, parameters).then((response) => {
        if (!response.ok) {
            throw response;
        }
        return response.json()
    })
}

export function post_json(url, payload, parameters) {

    if (parameters === undefined) {
        parameters = {}
    }

    if (parameters.headers === undefined) {
        parameters.headers = {}
    }

    parameters.method = "POST"
    parameters.headers['Content-Type'] = "application/json"
    parameters.body = JSON.stringify(payload)

    return fetch(url, parameters).then((response) => {return response.json()})
}

export function put_json(url, payload, parameters) {

    if (parameters === undefined) {
        parameters = {}
    }

    if (parameters.headers === undefined) {
        parameters.headers = {}
    }

    parameters.method = "PUT"
    parameters.headers['Content-Type'] = "application/json"
    parameters.body = JSON.stringify(payload)

    return fetch(url, parameters).then((response) => {return response.json()})
}

