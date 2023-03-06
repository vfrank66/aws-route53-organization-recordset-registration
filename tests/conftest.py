import json
import os
import sys
import uuid
from typing import Tuple

import attrdict
import boto3
import moto
import pytest
from moto import mock_sts

from . import test_constants

# make available to tests the src/ files for imports
my_path = os.path.dirname(os.path.abspath(__file__))
print(my_path)
sys.path.insert(0, my_path + "/../src/")
print(sys.path)


@pytest.fixture(scope="function")
def context():
    orig_env = os.environ.copy()

    class MockedContext:
        context = attrdict.AttrMap()
        # required for moto
        os.environ["AWS_ACCESS_KEY_ID"] = "foo"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "bar"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        # end required for moto
        os.environ["AwsAccountId"] = "111111111111"
        os.environ["AwsRegion"] = "us-east-1"
        os.environ["LOGGING_LEVEL"] = "INFO"
        os.environ["ENVIRONMENT"] = test_constants.TEST_ENVIRONMENT
        os.environ["ASSUME_ROLE_ARN"] = test_constants.TEST_ASSUME_ROLE_ARN
        os.environ["HALT_PROCESSING"] = test_constants.TEST_HALT_PROCESSING

        context.os = {"environ": os.environ}

        def get_remaining_time_in_millis(self):
            """Mocked method to return the remaining Lambda time in
            milliseconds."""
            return 840000

    return MockedContext()
    os.environ = orig_env


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def route53_client(scope="session"):
    moto.mock_route53().start()
    # clients
    client = boto3.client("route53")
    response = client.create_hosted_zone(
        Name="api.test.io",
        # VPC={
        #     'VPCRegion': 'us-east-1'|'us-east-2'|'us-west-1'|'us-west-2'|'eu-west-1'|'eu-west-2'|'eu-west-3'|'eu-central-1'|'ap-east-1'|'me-south-1'|'us-gov-west-1'|'us-gov-east-1'|'us-iso-east-1'|'us-iso-west-1'|'us-isob-east-1'|'me-central-1'|'ap-southeast-1'|'ap-southeast-2'|'ap-southeast-3'|'ap-south-1'|'ap-northeast-1'|'ap-northeast-2'|'ap-northeast-3'|'eu-north-1'|'sa-east-1'|'ca-central-1'|'cn-north-1'|'af-south-1'|'eu-south-1',
        #     'VPCId': 'string'
        # },
        CallerReference=str(uuid.uuid4()),
        # HostedZoneConfig={"Comment": "string", "PrivateZone": True | False},
        # DelegationSetId="string",
    )
    os.environ["DEST_HOSTED_ZONE_ID"] = response["HostedZone"]["Id"].replace("/hostedzone/", "")
    yield client


@pytest.fixture(scope="function")
def sts_client():
    with mock_sts():
        yield boto3.client("sts", region_name="us-east-1")


@pytest.fixture(scope="function")
def dynamodb_client() -> Tuple[boto3.client, boto3.resource]:
    with moto.mock_dynamodb2():
        yield [
            boto3.client("dynamodb", region_name="us-east-1"),
            boto3.resource("dynamodb", region_name="us-east-1"),
        ]


@pytest.fixture(scope="session")
def create_recordset_event():
    with open("tests/test-files/eventbridge.create.event.json") as json_file:
        eventbridge_event = json.load(json_file)
        yield eventbridge_event


@pytest.fixture(scope="session")
def bad_create_recordset_event():
    with open("tests/test-files/eventbridge.create.bad.event.json") as json_file:
        eventbridge_event = json.load(json_file)
        yield eventbridge_event


@pytest.fixture(scope="session")
def delete_recordset_event():
    with open("tests/test-files/eventbridge.delete.event.json") as json_file:
        eventbridge_event = json.load(json_file)
        yield eventbridge_event


@pytest.fixture(scope="session")
def regional_alb_recordset_event():
    with open("tests/test-files/eventbridge.regional.alb.event.json") as json_file:
        eventbridge_event = json.load(json_file)
        yield eventbridge_event
