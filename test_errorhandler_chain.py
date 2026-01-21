from flask import Blueprint

class ExceptionA(Exception):
    pass

class ExceptionB(Exception):
    pass

blueprint = Blueprint('test', __name__)

@blueprint.errorhandler(ExceptionB)
@blueprint.errorhandler(ExceptionA)
def handle(e):
    return "error"

print("Test completed")
