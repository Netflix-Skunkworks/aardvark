def test_advisor_data_create(mock_database):
    from aardvark.model import AdvisorData, db
    AdvisorData.create_or_update(
        9999,
        1111,
        "Swifties United",
        "swift",
        "taylor",
        1,
    )
    db.session.commit()

    record: AdvisorData = AdvisorData.query.filter(
        AdvisorData.item_id == 9999,
        AdvisorData.serviceNamespace == "swift",
    ).scalar()
    assert record
    assert record.id
    assert record.item_id == 9999
    assert record.lastAuthenticated == 1111
    assert record.lastAuthenticatedEntity == "taylor"
    assert record.serviceName == "Swifties United"
    assert record.serviceNamespace == "swift"
    assert record.totalAuthenticatedEntities == 1


def test_advisor_data_update(mock_database):
    from aardvark.model import AdvisorData, db
    AdvisorData.create_or_update(
        9999,
        0,
        "Pink Pony Club",
        "roan",
        None,
        0,
    )
    db.session.commit()

    record: AdvisorData = db.session.query(AdvisorData).filter(
        AdvisorData.id == 1,
    ).scalar()
    assert record
    assert record.lastAuthenticated == 0

    AdvisorData.create_or_update(
        9999,
        1111,
        "Pink Pony Club",
        "roan",
        "chappell",
        1,
    )
    db.session.commit()

    record: AdvisorData = db.session.query(AdvisorData).filter(
        AdvisorData.id == 1,
    ).scalar()
    assert record
    assert record.item_id == 9999
    assert record.lastAuthenticated == 1111
    assert record.lastAuthenticatedEntity == "chappell"
    assert record.serviceName == "Pink Pony Club"
    assert record.serviceNamespace == "roan"
    assert record.totalAuthenticatedEntities == 1


def test_advisor_data_update_older_last_authenticated(mock_database):
    from aardvark.model import AdvisorData, db
    AdvisorData.create_or_update(
        9999,
        1111,
        "Pink Pony Club",
        "roan",
        "chappell",
        1,
    )
    db.session.commit()

    record: AdvisorData = db.session.query(AdvisorData).filter(
        AdvisorData.id == 1,
        ).scalar()
    assert record
    assert record.lastAuthenticated == 1111

    # Calling create_or_update with a lower lastAuthenticated value should NOT update lastAuthenticated in the DB
    AdvisorData.create_or_update(
        9999,
        1000,
        "Pink Pony Club",
        "roan",
        "chappell",
        1,
    )
    db.session.commit()

    record: AdvisorData = db.session.query(AdvisorData).filter(
        AdvisorData.id == 1,
        ).scalar()
    assert record
    assert record.item_id == 9999
    assert record.lastAuthenticated == 1111
    assert record.lastAuthenticatedEntity == "chappell"
    assert record.serviceName == "Pink Pony Club"
    assert record.serviceNamespace == "roan"
    assert record.totalAuthenticatedEntities == 1


def test_advisor_data_update_zero_last_authenticated(mock_database):
    from aardvark.model import AdvisorData, db
    AdvisorData.create_or_update(
        9999,
        1111,
        "Pink Pony Club",
        "roan",
        "chappell",
        1,
    )
    db.session.commit()

    record: AdvisorData = db.session.query(AdvisorData).filter(
        AdvisorData.id == 1,
        ).scalar()
    assert record
    assert record.lastAuthenticated == 1111

    # Calling create_or_update with a zero lastAuthenticated value SHOULD update lastAuthenticated in the DB
    AdvisorData.create_or_update(
        9999,
        0,
        "Pink Pony Club",
        "roan",
        "",
        0,
    )
    db.session.commit()

    record: AdvisorData = db.session.query(AdvisorData).filter(
        AdvisorData.id == 1,
        ).scalar()
    assert record
    assert record.item_id == 9999
    assert record.lastAuthenticated == 0
    assert record.lastAuthenticatedEntity == ""
    assert record.serviceName == "Pink Pony Club"
    assert record.serviceNamespace == "roan"
    assert record.totalAuthenticatedEntities == 0
