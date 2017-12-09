
import {
    TEST_MESSSAGE_CREATE,
    TEST_MESSSAGE_DELETE,
    TEST_MESSSAGE_GET_ALL,
    TEST_MESSSAGE_SUCCESS,
    TEST_MESSSAGE_FAILURE,
    TEST_RANDOM_INT,
} from '../constants/index';

import { parseJSON } from '../utils/misc';
import { get_random_int, create_message, get_all_messages, delete_message } from '../utils/http_functions';

export function messageRequest(messageType) {
    return {type: messageType}
}

export function getRandomIntSuccess(value) {
    return {
        type: TEST_RANDOM_INT,
        payload: {
            value,
        },
    };
}

export function messageSuccess(messages) {
    return {
        type: TEST_MESSSAGE_SUCCESS,
        payload: {
            messages,
        },
    };
}

export function messageFailure(error) {
    return {
        type: TEST_MESSSAGE_FAILURE,
        payload: {
            status: 500,
            statusText: error.message,
        },
    };
}

export function getRandomInt() {
    return function (dispatch) {
        return get_random_int()
            .then(parseJSON)
            .then(response => {
                dispatch(getRandomIntSuccess(response.value));
            })
            .catch(error => {
                dispatch(messageFailure({"status":400,
                                         "statusText":"none"}));
            })
    }
}

export function createMessage(text) {
    return function (dispatch) {
        dispatch(messageRequest(TEST_MESSSAGE_CREATE));
        return create_message(text)
            .then(parseJSON)
            .then(response => {
                dispatch(messageSuccess(response.messages));
            })
            .catch(error => {
                dispatch(messageFailure(error));
            })
    }
}

export function getAllMessages() {
    return function (dispatch) {
        dispatch(messageRequest(TEST_MESSSAGE_GET_ALL));
        return get_all_messages()
            .then(parseJSON)
            .then(response => {
                dispatch(messageSuccess(response.messages));
            })
            .catch(error => {
                dispatch(messageFailure(error));
            })
    }
}

export function deleteMessage(id) {
    return function (dispatch) {
        dispatch(messageRequest(TEST_MESSSAGE_DELETE));
        return delete_message(id)
            .then(parseJSON)
            .then(response => {
                dispatch(messageSuccess(response.messages));
            })
            .catch(error => {
                dispatch(messageFailure(error));
            })
    }
}