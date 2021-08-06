import json
from flask import Flask
from flask import request, Response
from typing import Dict, List


def create_app() -> Flask:
    app = Flask(__name__)

    app.data: Dict[str:Dict[str:List[str]]] = {}

    @app.route("/", methods=["GET"])
    def index() -> Response:
        return Response(json.dumps(app.data), status=200, mimetype='application/json')

    @app.route("/push_list", methods=["POST"])
    def push_list() -> Response:
        json_data = request.json
        build_id = json_data.get("build_id")
        test_suite = json_data.get("test_suite")
        tests = json_data.get("tests")

        if build_id in app.data:
            if test_suite in app.data[build_id]:
                return Response(json.dumps({"details": "This tests list exists already."}), status=412,
                                mimetype='application/json')
        else:
            app.data[build_id] = {}

        app.data[build_id][test_suite] = tests

        return Response(json.dumps({"details": "OK"}), status=201, mimetype='application/json')

    @app.route("/next_test", methods=["GET"])
    def next_test() -> Response:
        build_id = str(request.args.get("build_id", ""))
        test_suite = str(request.args.get("test_suite", ""))

        if build_id == "" or test_suite == "":
            return Response(json.dumps({"details": ""}), status=400, mimetype='application/json')
        if build_id not in app.data or test_suite not in app.data[build_id]:
            return Response(json.dumps({"details": ""}), status=404, mimetype='application/json')
        if len(app.data[build_id][test_suite]) == 0:
            return Response(json.dumps({"details": ""}), status=200, mimetype='application/json')

        first_test = app.data[build_id][test_suite][0]

        del app.data[build_id][test_suite][0]

        if len(app.data[build_id][test_suite]) == 0:
            del app.data[build_id][test_suite]
            if len(app.data[build_id]) == 0:
                del app.data[build_id]

        return Response(json.dumps({"details": first_test}), status=200, mimetype='application/json')

    return app
