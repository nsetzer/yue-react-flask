

from ..framework.application import FlaskApp
from ..framework.web_resource import WebResource, get

from ..config import Config

from flask import jsonify, render_template

from ..service.audio_service import AudioService
from ..service.transcode_service import TranscodeService
from ..service.user_service import UserService

from .resource.user import UserResource

class AppResource(WebResource):
    """docstring for AppResource
    """

    def __init__(self):
        super(AppResource, self).__init__()
        self.register('/', self.index1, ['GET'])
        self.register('/<path:path>', self.index2, ['GET'])
        self.register('/health', self.health, ['GET'])
        self.register('/.well-known/<path:path>', self.webroot, ['GET'])

    def index1(self, app, path):
        return render_template('index.html')

    def index2(self, app, path):
        return render_template('index.html')

    def health(self, app):
        return jsonify(result="OK")

    def webroot(self, app, path):
        base = os.path.join(os.getcwd(), ".well-known")
        return send_from_directory(base, path)

class YueApp(FlaskApp):
    """docstring for YueApp"""
    def __init__(self, config):
        super(YueApp, self).__init__(config)

        self.audio_service = AudioService(self.db, self.db.tables)
        self.transcode_service = TranscodeService(self.db, self.db.tables)
        self.user_service = UserService(self.db, self.db.tables)

        self.add_resource(AppResource())
        self.add_resource(UserResource(self.user_service))

def main():

    cfg = Config.init("config/development/application.yml")

    app = YueApp(cfg)

    routes = app.list_routes()
    for endpoint, methods, url in routes:
        print("{:30s} {:20s} {}".format(endpoint, methods, url))

    app.run()

if __name__ == '__main__':
    main()