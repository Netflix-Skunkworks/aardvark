import yaml

from aardvark.config import create_config


def test_create_config(temp_config_file):
    create_config(
        aardvark_role="role",
        swag_bucket="bucket",
        swag_filter="filter",
        swag_service_enabled_requirement="service",
        arn_partition="aws",
        sqlalchemy_database_uri="sqlite://////////////hi.db",
        sqlalchemy_track_modifications=True,
        num_threads=99,
        region="us-underground-5",
        filename=temp_config_file,
        environment="testtesttest",
    )

    with open(temp_config_file, "r") as f:
        file_data = yaml.safe_load(f)

    assert file_data["testtesttest"]["AWS_ROLENAME"] == "role"
    assert file_data["testtesttest"]["AWS_REGION"] == "us-underground-5"
    assert file_data["testtesttest"]["AWS_ARN_PARTITION"] == "aws"
    assert file_data["testtesttest"]["SWAG"]["bucket"] == "bucket"
    assert file_data["testtesttest"]["SWAG"]["filter"] == "filter"
    assert file_data["testtesttest"]["SWAG"]["service_enabled_requirement"] == "service"
    assert file_data["testtesttest"]["UPDATER_NUM_THREADS"] == 99
    assert file_data["testtesttest"]["SQLALCHEMY_DATABASE_URI"] == "sqlite://////////////hi.db"
    assert file_data["testtesttest"]["SQLALCHEMY_TRACK_MODIFICATIONS"] is True
