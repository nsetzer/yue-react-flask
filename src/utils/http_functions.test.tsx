
import { expect, assert } from 'chai';

import { user_queue_get,
         user_queue_set,
         user_queue_populate
    } from "./http_functions"

it('should get/set the queue', async function() {

    let song_ids : Array<string> = []

    let token : string = "Basic " + btoa("user000:user000")

    console.log("test1 ")

/*
    try {
        let res = await user_queue_set("invalid", song_ids)
    } catch(e) {
        console.log(e)
        expect(e.request.status).to.eq(401)
    }
    */

    console.log("test2 ")
    try {
        let res : { "result" : any };

        res = await user_queue_set(token, song_ids)

        res = await user_queue_get(token)

        res = await user_queue_populate(token)

        res = await user_queue_get(token)
        //expect(res.status).to.eq(200)
    } catch(e) {
        console.log(e)
    }

    /*

    function dispatch(state) {
        states.push(state)
        return state
    }

    // result is set to the final dispatched value
    let result = await authActions.loginUser(props, email, password, "/main")(dispatch);

    expect(result.type).to.eq(LOGIN_USER_SUCCESS)
    //assert.typeOf(result.payload.token, 'string')

    // states will contain all dispatched states.
    expect(states[0].type).to.eq(LOGIN_USER_REQUEST)
    expect(states[1].type).to.eq(LOGIN_USER_SUCCESS)

    result = await authActions.logoutAndRedirect(props)(dispatch);
    expect(result.type).to.eq(LOGOUT_USER)
    */
});
