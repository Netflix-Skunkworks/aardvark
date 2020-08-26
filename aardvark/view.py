# ensure absolute import for python3
from __future__ import absolute_import

from flask import Blueprint, abort, jsonify, request

from aardvark.persistence.sqlalchemy import SQLAlchemyPersistence

advisor_bp = Blueprint("advisor", __name__)
session = SQLAlchemyPersistence()._create_session()


@advisor_bp.teardown_request
def shutdown_session(exception=None):
    session.remove()


# undocumented convenience pass-through so we can query directly from browser
@advisor_bp.route("/advisors")
def get():
    return post()


@advisor_bp.route("/advisors")
def post():
    """Get access advisor data for role(s)
    Returns access advisor information for role(s) that match filters
    ---
    consumes:
      - 'application/json'
    produces:
      - 'application/json'

    parameters:
      - name: page
        in: query
        type: integer
        description: return results from given page of total results
        required: false
      - name: count
        in: query
        type: integer
        description: specifies how many results should be return per page
        required: false
      - name: combine
        in: query
        type: boolean
        description: combine access advisor data for all results [Default False]
        required: false
      - name: phrase
        in: query
        type: string
        description: TODO
        required: false
      - name: regex
        in: query
        type: string
        description: TODO
        required: false
      - name: arn
        in: query
        type: string
        description: TODO
        required: false

    definitions:
      AdvisorData:
        type: object
        properties:
          lastAuthenticated:
            type: number
          lastAuthenticatedEntity:
            type: string
          lastUpdated:
            type: string
          serviceName:
            type: string
          serviceNamespace:
            type: string
          totalAuthenticatedEntities:
            type: number
      QueryBody:
        type: object
        properties:
          phrase:
            type: string
          regex:
            type: string
          arn:
            type: array
            items: string
      Results:
        type: array
        items:
          $ref: '#/definitions/AdvisorData'

    responses:
      200:
        description: Query successful, results in body
        schema:
          $ref: '#/definitions/AdvisorData'
      400:
        description: Bad request - error message in body
    """
    try:
        page = int(request.args.get("page", 1))
        count = int(request.args.get("count", 30))
        combine = request.args.get("combine", type=str, default="false")
        combine = combine.lower() == "true"
        phrase = request.args.get("phrase")
        regex = request.args.get("regex", default=None)
        arns = request.args.get("arn")
        arns = arns.split(",") if arns else []
    except Exception as e:
        raise abort(400, str(e))

    values = SQLAlchemyPersistence().get_role_data(
        page=page,
        count=count,
        combine=combine,
        phrase=phrase,
        arns=arns,
        regex=regex,
        session=session,
    )

    return jsonify(values)
