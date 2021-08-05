from typing import Dict, List

from flask import Flask
from flask import request


def create_app() -> Flask:
    app = Flask(__name__)

    app.data: Dict[str:Dict[str:List[str]]] = {}

    @app.route("/")
    def index() -> str:
        print(app.data)
        return str(app.data)

    @app.route("/push_list", methods=["POST"])
    def push_list() -> dict:
        json_data = request.json
        build_id = json_data.get("build_id")
        test_suite = json_data.get("test_suite")
        tests = json_data.get("tests")

        if build_id in app.data:
            if test_suite in app.data[build_id]:
                return {"error": "This pipeline id already exists."}
        else:
            app.data[build_id] = {}

        app.data[build_id][test_suite] = tests

        return {"status": "OK"}

    @app.route("/next_test", methods=["GET"])
    def next_test() -> str:
        build_id = str(request.args.get("build_id", ""))
        test_suite = str(request.args.get("test_suite", ""))

        if build_id == "" or test_suite == "":
            return ""

        if build_id not in app.data:
            return ""

        if test_suite not in app.data[build_id]:
            return ""

        if len(app.data[build_id][test_suite]) == 0:
            return ""

        first_test = app.data[build_id][test_suite][0]

        del app.data[build_id][test_suite][0]

        if len(app.data[build_id][test_suite]) == 0:
            del app.data[build_id][test_suite]
            if len(app.data[build_id]) == 0:
                del app.data[build_id]

        return first_test

    return app
