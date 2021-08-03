from flask import Flask
from flask import request

def create_app():
    app = Flask(__name__)

    app.data = {}

    @app.route("/")
    def index():
        print(app.data)
        return app.data

    @app.route("/push_list", methods=['POST'])
    def push_list():
        pipeline_id = str(request.form["pipeline_id"])
        tests = str(request.form["tests"])

        if pipeline_id in app.data:
            return {"error": "This pipeline id already exists."}

        app.data[pipeline_id] = tests.split(":")

        print(app.data)

        return {"status": "OK"}


    @app.route("/next_test", methods=['GET'])
    def next_test():
        pipeline_id = str(request.args.get("pipeline_id", ""))

        if pipeline_id == "":
            return ""

        if pipeline_id not in app.data:
            return ""

        tests_list = app.data[pipeline_id]

        if len(tests_list) == 0:
            return ""

        first_test = tests_list[0]

        del tests_list[0]

        if len(tests_list) == 0:
            del app.data[pipeline_id]
        else:
            app.data[pipeline_id] = tests_list
            print(app.data[pipeline_id])

        return first_test

    return app
