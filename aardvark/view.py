#ensure absolute import for python3
from __future__ import absolute_import

import better_exceptions  # noqa
import datetime
import json

from flask import abort, jsonify
from flask import Blueprint
from flask_restful import Api, Resource, reqparse
from flask import Flask
import sqlalchemy as sa

from aardvark.model import AWSIAMObject


mod = Blueprint('advisor', __name__)
api = Api(mod)
app = Flask(__name__)


class RoleSearch(Resource):
    """
    Search for roles by phrase, regex, or by ARN.
    """
    def __init__(self):
        super(RoleSearch, self).__init__()
        self.reqparse = reqparse.RequestParser()

    def combine(self, aa):
        del aa['count']
        del aa['page']
        del aa['total']

        usage = dict()
        for arn, services in aa.items():
            for service in services:
                namespace = service.get('serviceNamespace')
                last_authenticated = service.get('lastAuthenticated')
                if namespace not in usage:
                    usage[namespace] = service
                else:
                    count_entities = usage[namespace]['totalAuthenticatedEntities'] + service['totalAuthenticatedEntities']
                    if last_authenticated > usage[namespace]['lastAuthenticated']:
                        usage[namespace] = service
                    usage[namespace]['totalAuthenticatedEntities'] = count_entities

        for namespace, service in usage.items():
            last_authenticated = service['lastAuthenticated']
            dt_last_authenticated = datetime.datetime.fromtimestamp(last_authenticated / 1e3)
            dt_starting = datetime.datetime.utcnow() - datetime.timedelta(days=90)
            usage[namespace]['USED_LAST_90_DAYS'] = dt_last_authenticated > dt_starting

        return jsonify(usage)

    # undocumented convenience pass-through so we can query directly from browser
    @app.route('/advisors')
    def get(self):
        return(self.post())

    @app.route('/advisors')
    def post(self):
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
          - name: query
            in: body
            schema:
              $ref: '#/definitions/QueryBody'
            description: |
                one or more query parameters in a JSON blob.  Filter
                parameters build on eachother.

                Options are:

                1) arn list - a list of one or more specific arns

                2) phrase matching - search for ARNs like the one supplied

                3) regex - match a supplied regular expression.

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
        self.reqparse.add_argument('page', type=int, default=1)
        self.reqparse.add_argument('count', type=int, default=30)
        self.reqparse.add_argument('combine', type=str, default='false')
        self.reqparse.add_argument('phrase', default=None)
        self.reqparse.add_argument('regex', default=None)
        self.reqparse.add_argument('arn', default=None, action='append')
        try:
            args = self.reqparse.parse_args()
        except Exception as e:
            abort(400, str(e))

        page = args.pop('page')
        count = args.pop('count')
        combine = args.pop('combine', 'false')
        combine = combine.lower() == 'true'
        phrase = args.pop('phrase', '')
        arns = args.pop('arn', [])
        regex = args.pop('regex', '')
        items = None

        # default unfiltered query
        query = AWSIAMObject.query

        try:
            if phrase:
                query = query.filter(AWSIAMObject.arn.ilike('%' + phrase + '%'))

            if arns:
                query = query.filter(
                    sa.func.lower(AWSIAMObject.arn).in_([arn.lower() for arn in arns]))

            if regex:
                query = query.filter(AWSIAMObject.arn.regexp(regex))

            items = query.paginate(page, count)
        except Exception as e:
            abort(400, str(e))

        if not items:
            items = AWSIAMObject.query.paginate(page, count)

        values = dict(page=items.page, total=items.total, count=len(items.items))
        for item in items.items:
            item_values = []
            for advisor_data in item.usage:
                item_values.append(dict(
                    lastAuthenticated=advisor_data.lastAuthenticated,
                    serviceName=advisor_data.serviceName,
                    serviceNamespace=advisor_data.serviceNamespace,
                    lastAuthenticatedEntity=advisor_data.lastAuthenticatedEntity,
                    totalAuthenticatedEntities=advisor_data.totalAuthenticatedEntities,
                    lastUpdated=item.lastUpdated
                ))
            values[item.arn] = item_values

        if combine and items.total > len(items.items):
            abort(400, "Error: Please specify a count of at least {}.".format(items.total))
        elif combine:
            return self.combine(values)

        return jsonify(values)


api.add_resource(RoleSearch, '/advisors')
