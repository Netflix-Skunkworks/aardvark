import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func as sa_func

from aardvark.exceptions import DatabaseException, CombineException
from aardvark.models.sqlalchemy.aws_iam_object import AWSIAMObject
from aardvark.models.sqlalchemy.utils import db_session, Base


def combine_results(access_advisor_data: Dict[str, Any]):
    usage = dict()
    for arn, services in access_advisor_data.items():
        for service in services:
            namespace = service.get("serviceNamespace")
            last_authenticated = service.get("lastAuthenticated")
            if namespace not in usage:
                usage[namespace] = service
            else:
                count_entities = (
                    usage[namespace]["totalAuthenticatedEntities"]
                    + service["totalAuthenticatedEntities"]
                )
                if last_authenticated > usage[namespace]["lastAuthenticated"]:
                    usage[namespace] = service
                usage[namespace]["totalAuthenticatedEntities"] = count_entities

    for namespace, service in usage.items():
        last_authenticated = service["lastAuthenticated"]
        dt_last_authenticated = datetime.datetime.fromtimestamp(
            last_authenticated / 1e3
        )
        dt_starting = datetime.datetime.utcnow() - datetime.timedelta(days=90)
        usage[namespace]["USED_LAST_90_DAYS"] = dt_last_authenticated > dt_starting

    return usage


def get_role_data(
    page: int = 0,
    count: int = 0,
    combine: bool = False,
    phrase: str = "",
    arns: Optional[List[str]] = None,
    regex: str = "",
):
    offset = (page - 1) * count if page else 0
    limit = count
    # default unfiltered query
    query = AWSIAMObject.query

    try:
        if phrase:
            query = query.filter(AWSIAMObject.arn.ilike("%" + phrase + "%"))

        if arns:
            query = query.filter(
                sa_func.lower(AWSIAMObject.arn).in_([arn.lower() for arn in arns])
            )

        if regex:
            query = query.filter(AWSIAMObject.arn.regexp(regex))

        total = query.count()

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        items = query.all()
    except Exception as e:
        raise DatabaseException("Could not retrieve roles from database: %s", e)

    if not items:
        items = AWSIAMObject.query.offset(offset).limit(limit).all()

    values = dict(page=page, total=total, count=len(items))
    for item in items:
        item_values = []
        for advisor_data in item.usage:
            item_values.append(
                dict(
                    lastAuthenticated=advisor_data.lastAuthenticated,
                    serviceName=advisor_data.serviceName,
                    serviceNamespace=advisor_data.serviceNamespace,
                    lastAuthenticatedEntity=advisor_data.lastAuthenticatedEntity,
                    totalAuthenticatedEntities=advisor_data.totalAuthenticatedEntities,
                    lastUpdated=item.lastUpdated,
                )
            )
        values[item.arn] = item_values

    if combine and total > len(items):
        raise CombineException(
            "Error: Please specify a count of at least {}.".format(items.total)
        )
    elif combine:
        return combine_results(values)

    return values
