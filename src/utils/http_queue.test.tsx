
import { expect, assert } from 'chai';

import { user_queue_get,
         user_queue_set,
         user_queue_populate
    } from "./http_queue"

it('should get/set/populate the queue', async function() {

    let song_ids : Array<string> = []
    let token : string = "Basic " + btoa("user000:user000")

    try {
        let res = await user_queue_set("invalid", song_ids)
    } catch(e) {
        expect(e.statusCode).to.eq(401)
    }

    let res1 : { "result" : any } = await user_queue_set(token, song_ids)
    assert.equal(res1['result'], "OK")

    let res2 : { "result" : any } = await user_queue_get(token)
    assert.equal(res2['result'].length, 0)

    let res3 : { "result" : any } = await user_queue_populate(token)
    // the result needs to be non-empty, assert at least 5 songs
    // so that we have some data to work on later on in the test
    assert.isAbove(res3['result'].length, 5)

    let res4 : { "result" : any } = await user_queue_get(token)

    let songs1 : Array<any> = res3.result;
    let songs2 : Array<any> = res4.result;
    assert.equal(songs1.length, songs2.length)
    for (let i=0; i < songs1.length; i++) {
        assert.equal(songs1[0].id, songs2[0].id)
    }

    // create a new set of 5 songs
    // set the song queue to this set.
    // verify that the queue was set correctly

    for (let i=0; i < 5; i++) {
        song_ids.push(songs1[i].id);
    }

    // set the queue to the 5 chosen songs
    let res5 : { "result" : any } = await user_queue_set(token, song_ids)
    assert.equal(res5['result'], "OK")

    // verify that the queue now contains those 5 songs
    let res6 : { "result" : any } = await user_queue_get(token)
    let songs3 : Array<any> = res6.result

    assert.equal(songs3.length, 5)
    for (let i=0; i < 5; i++) {
        assert.equal(songs1[0].id, songs3[0].id)
    }

});
