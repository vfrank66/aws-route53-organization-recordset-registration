import os

import boto3


def get_adler_cross_account_iam():
    """Return the correct role arn to assume in the ADLER accounts."""
    return os.environ["ASSUME_ROLE_ARN"]


def get_sts_role_session():
    """Create and return new credentials assumed from the ADLER accout."""
    sts = boto3.client("sts")
    sts_role_cred = sts.assume_role(RoleArn=get_adler_cross_account_iam(),
                                    RoleSessionName="SyncRole",
                                    DurationSeconds=900)
    return [
        sts_role_cred["Credentials"]["AccessKeyId"],
        sts_role_cred["Credentials"]["SecretAccessKey"],
        sts_role_cred["Credentials"]["SessionToken"],
    ]
