# Overview

This is the lambda function that is triggered by a `aws.route53` private api creation event, it is the filtered to ensure that it only processes `Company` apis. It will create a Route53 recordset in companies management  AWS account which makes available to local machines the private api since the management route53 hosted zones are replicated to on-prem DNS servers.

To run this you will need access to deploy a iam role into your companies organization account. Listed below in the readme is the iam role cfn for a this cross account role. Once created that be input into the parameters environments(assuming each deployment environment has its own aws account if not then you can consolidate).

One parameter environment:
```json
[
    {
        "ParameterKey": "Environment",
        "ParameterValue": "dev"
    },
    {
        "ParameterKey": "IamRoleArn",
        "ParameterValue": "<insert role with permissions to both aws account route53 recordsets>" <---------------
    },
    // optional if you want notification of errors in a lambda function
    {
        "ParameterKey": "AlarnTargetArn",
        "ParameterValue": ""
    },
    // optinoal if you want to filter recordset upsert to a specific domain
    {
        "ParameterKey": "CompanyDomainFilter",
        "ParameterValue": "test.api.io"
    },
]
```

If you have a on call notifaction system the AlarmTargetArn will report to that target for failures in the lambda function on general errors and out of memory errors.

## Python

This is a python3.9 project, so you must use >3.9.7 as stated in the setup.py.

## Development

When developing and making changes before commiting always run `scripts/run-tests.sh`. What `run-test.sh` does is executes `yapf` package when in addition to linting actually formatts the code so all checked in code will be consistent, second it runs the linter `flake8`, third is runs `pytests` which will tell you if you have the test coverage.

`cd scripts && sh run-tests.sh`

.vscode/settings.json
```json
{
    "python.pythonPath": "venv/bin/python",
    "python.testing.unittestEnabled": false,
    "python.testing.nosetestsEnabled": false,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ]
}

```
.vscode/launch.json
```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        
        {
            "name": "SAND: Main",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/handler.py",
            "console": "integratedTerminal",
            "args": [],
            "env": {
                "AWS_REGION": "us-east-1",
                "AWS_PROFILE": "default",
                "ENVIRONMENT": "sand",
                "ASSUME_ROLE_ARN": "<insert cross account iam role>",
            }
        },
        {
            "name": "STG: Main",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/handler.py",
            "console": "integratedTerminal",
            "args": [],
            "env": {
                "AWS_REGION": "us-east-1",
                "AWS_PROFILE": "default",
                "ENVIRONMENT": "stg",
                "ASSUME_ROLE_ARN":"<insert cross account iam role>",
            }
        },
        {
            "name": "PROD: Main",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/handler.py",
            "console": "integratedTerminal",
            "args": [],
            "env": {
                "AWS_REGION": "us-east-1",
                "AWS_PROFILE": "default",
                "ENVIRONMENT": "prod",
                "ASSUME_ROLE_ARN": "<insert cross account iam role>",
            }
        },
        {
            "name": "Python: Pytest",
            "type": "python",
            "request": "launch",
            "module": "pytest"
        },
    ]
}
```

You will also need to install the `Python` extension in vscode. With these settings and the python extension you can run/discover tests through the vscode UI on the right.

# Deployment if starting in new region 

1. Run/deploy 
```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: Deploys cross account role for Route53 record set registeration with AWS accounts.

Parameters:
  OrgId:
    Type: String
    Description: AWS Organization ID
    Default: <insert default org id>
Mappings:
  AccountId:
    environments:
      ID:
        - 123 #  dev
        - 234 #  stg
        - 345 #  prod

Resources:
  CrossAccountIAMRole:
    Type: AWS::IAM::Role
    Properties:
      Path: /
      RoleName: CrossAccountRoute53
      Description: The role for cross account lambda functions to assume when needing register a new Route53 recordset.
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              AWS: '*'
            Condition:
              StringEquals:
                aws:PrincipalOrgID: !Ref OrgId
                aws:PrincipalAccount: !FindInMap [AccountId, environments, ID]
            Action:
              - sts:AssumeRole
      Policies:
        - PolicyName: route53-registration
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - "route53:GetChange"
                  - "route53:ChangeResourceRecordSets"
                  - "route53:ChangeTagsForResource"
                  - "route53:ListResourceRecordSets"
                Resource: "*" 
``` 
in the organizations management account and make sure the IAM role is correctly applied locally and in the parameters.  
2. Run/deploy `aws-route53-organization-recordset-registration` in the non-management account(s).
