
import { expect, assert } from 'chai';

import { user_get_queue,
         user_set_queue } from "./http_functions"

it('should get/set the queue', async function() {

    let song_ids : Array<string> = []

    let token : string = "Basic " + btoa("user000:user000")

    console.log("test1 ")

    try {
        let res = await user_set_queue("invalid", song_ids)
    } catch(e) {
        expect(e.request.status).to.eq(401)
    }

    console.log("test2 ")
    try {
        res = await user_get_queue(token, song_ids)
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
