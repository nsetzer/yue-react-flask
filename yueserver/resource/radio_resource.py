

import os
import sys
import logging

from flask import jsonify, render_template, g, request, send_file

from ..framework.web_resource import WebResource, \
    get, post, put, delete, param, body, compressed, httpError, \
    int_range, int_min, send_generator, null_validator, \
    OpenApiParameter, Integer, String, Boolean, \
    JsonOpenApiBody, ArrayOpenApiBody, StringOpenApiBody


class RadioResource(WebResource):

    def __init__(self, user_service, radio_service):
        super(RadioResource, self).__init__("/api/radio")

        self.user_service = user_service
        self.radio_service = radio_service

    @get("video/info")
    @param("videoId", type_=String())
    @compressed
    def get_video_info(self):

        info = self.radio_service.getVideoInfo(g.args.videoId)

        return jsonify({"result": info})