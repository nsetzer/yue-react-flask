
import { expect, assert } from 'chai';

import { user_library_search,
         user_library_domain_info,
    } from "./http_library"

it('should return songs from the database', async function() {

    let song_ids : Array<string> = []
    let token : string = "Basic " + btoa("user000:user000")

    try {
        let res = await user_library_search("invalid", "")
    } catch(e) {
        expect(e.statusCode).to.eq(401)
    }

    // a blank search should return the first page of a non empty result
    let res1 = await user_library_search(token, "")
    assert.isAbove(res1['result'].length, 0)
    assert.equal(res1['page'], 0)
    assert.isAbove(res1['page_size'], 0)

});

it('should return domain info', async function() {

    let song_ids : Array<string> = []
    let token : string = "Basic " + btoa("user000:user000")


    // check that the domain info contains the expected fields
    // should contain 2 dictionaries and a total count of indexed files
    let res1 = await user_library_domain_info(token)
    assert.isAbove(Object.keys(res1['result']['artists']).length, 0)
    assert.isAbove(Object.keys(res1['result']['genres']).length, 0)
    assert.isAbove(res1['result']['num_songs'], 0)

});
