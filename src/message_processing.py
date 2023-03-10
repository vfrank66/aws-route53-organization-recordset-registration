"""Process Route53 eventbridge event."""
import json
import logging
import os
from enum import Enum

import boto3

import _utils
import sts

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RecordSetChangeAction(str, Enum):
    """Route53 record set change action."""

    create = "CREATE"
    delete = "DELETE"
    upsert = "UPSERT"


def print_event(event_message, event_type=None):
    """Print the event message."""
    logger.info("Recieved following event {type}".format(type=event_type))
    logger.info("--------------------------------------------------")
    logger.info(event_message)
    logger.info("--------------------------------------------------")


def change_resource_record_sets(
    route53_client: boto3.client,
    change_action: RecordSetChangeAction,
    recordset_name: str,
    recordset_type: str,  # 'SOA'|'A'|'TXT'|'NS'|'CNAME'|'MX'|'NAPTR'|'PTR'|'SRV'|'SPF'|'AAAA'|'CAA'|'DS',
    alias_target_hosted_zone_id: str,
    alias_target_dns_name: str,
    alias_target_eval_target_health: bool = False,
    hosted_zone_id: str = "<insert default for company>",
):
    """Route53 change_resource_record_sets, created for unit testing."""
    return route53_client.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Comment":
            "Autogenerated from aws-route53-organization-recordset-registration for AWS Route53 recordsets.",
            "Changes": [
                {
                    "Action": change_action,
                    "ResourceRecordSet": {
                        "Name": recordset_name,  # <url>.<domain>
                        "Type": recordset_type,
                        "AliasTarget": {
                            "HostedZoneId": alias_target_hosted_zone_id, 
                            "DNSName":
                            alias_target_dns_name,  
                            "EvaluateTargetHealth": alias_target_eval_target_health,
                        },
                    },
                },
            ],
        },
    )


def list_change_recordset(
    route53_client: boto3.client,
    recordset_name: str,
    recordset_type: str,  # 'SOA'|'A'|'TXT'|'NS'|'CNAME'|'MX'|'NAPTR'|'PTR'|'SRV'|'SPF'|'AAAA'|'CAA'|'DS',
    max_items: str = "1",
    hosted_zone_id: str = "Z35UT56EKXRG2H",
):
    """List change record sets."""
    return route53_client.list_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        StartRecordName=recordset_name,
        StartRecordType=recordset_type,
        MaxItems=max_items,
    )


def wait_for_recordset_change(route53_client: boto3.client, change_id: str):
    """Wait for."""
    waiter = route53_client.get_waiter("resource_record_sets_changed")
    # 30 seconds x 20 = 10 mins
    waiter.wait(
        Id=change_id,
        WaiterConfig={
            "Delay": 30,  # The amount of time in seconds to wait between attempts
            "MaxAttempts": 20,  # The maximum number of attempts to be made
        },
    )


def modify_route53_change_recordset(
    route53_client: boto3.client,
    change_action: RecordSetChangeAction,
    recordset_name: str,
    recordset_type: str,  # 'SOA'|'A'|'TXT'|'NS'|'CNAME'|'MX'|'NAPTR'|'PTR'|'SRV'|'SPF'|'AAAA'|'CAA'|'DS',
    alias_target_hosted_zone_id: str,
    alias_target_dns_name: str,
    alias_target_eval_target_health: bool = False,
    hosted_zone_id: str = "<insert default for company>",
):
    """Modify change recordset."""
    logger.info(f"Creating change recordset in {recordset_name}")
    try:
        if change_action == RecordSetChangeAction.delete:
            existing_record_set = list_change_recordset(
                route53_client=route53_client,
                recordset_name=recordset_name,
                recordset_type=recordset_type,
                max_items="1",
                hosted_zone_id=hosted_zone_id,
            )["ResourceRecordSets"]
            if len(existing_record_set) > 0:
                existing_evaluate_target_health = existing_record_set[0]["AliasTarget"]["EvaluateTargetHealth"]
                if existing_evaluate_target_health != alias_target_eval_target_health:
                    logger.warn(
                        "Found existing record set but the EvaluateTargetHealth, this can happen when a user maunally creates the RecordSet. "
                        + "The problem is that we cannot delete if this differs so changing first then deleting.")
                    alias_target_eval_target_health = existing_evaluate_target_health
        response = change_resource_record_sets(
            route53_client=route53_client,
            change_action=change_action,
            recordset_name=recordset_name,
            recordset_type=recordset_type,
            alias_target_hosted_zone_id=alias_target_hosted_zone_id,
            alias_target_dns_name=alias_target_dns_name,
            alias_target_eval_target_health=alias_target_eval_target_health,
            hosted_zone_id=hosted_zone_id,
        )
        return response
    except route53_client.exceptions.InvalidChangeBatch as ce:
        # botocore.errorfactory.InvalidChangeBatch: An error occurred (InvalidChangeBatch) when calling the ChangeResourceRecordSets operation:
        # [RRSet with DNS name <url>.<company domain name>., type A, SetIdentifier Simple, and Region Name=us-east-1 cannot be created because a non-latency RRSet with the same name and type already exists.]

        # otocore.errorfactory.InvalidChangeBatch: An error occurred (InvalidChangeBatch) when calling the ChangeResourceRecordSets operation:
        # [Tried to delete resource record set [name='<url>.<company domain name>.', type='A', set-identifier='Simple'] but it was not found]
        ex_message = ce.response["Error"]["Message"]
        logger.error(ce)
        if "Tried to delete resource record set " in ex_message and "but it was not found" in ex_message:
            # noop
            return None
        if "Tried to create resource record set " in ex_message and "but it already exists" in ex_message:
            # noop
            return modify_route53_change_recordset(
                route53_client=route53_client,
                change_action=RecordSetChangeAction.upsert,
                recordset_name=recordset_name,
                recordset_type=recordset_type,
                alias_target_hosted_zone_id=alias_target_hosted_zone_id,
                alias_target_dns_name=alias_target_dns_name,
                alias_target_eval_target_health=alias_target_eval_target_health,
                hosted_zone_id=hosted_zone_id,
            )
        raise ce


def process_message(event, context):
    """Process the lambda event message."""
    try:
        # env = os.environ.get("ENVIRONMENT", None)
        dest_hosted_zone_id = os.environ.get(
            "DEST_HOSTED_ZONE_ID",
            "<insert default hosted zone for domain>")  #  zone id - created for unit testing
        company_domain_filter = os.environ.get("COMPANY_DOMAIN_FILTER", None)
        [aid, sak, stok] = sts.get_sts_role_session()
        dest_route53_client = boto3.client("route53",
                                           aws_access_key_id=aid,
                                           aws_secret_access_key=sak,
                                           aws_session_token=stok)

        event_details = event["detail"]["requestParameters"]

        return_status = {}
        for event_changes in event_details["changeBatch"]["changes"]:
            logger.info(f"Processing changes {json.dumps(event_changes, indent=4)}")
            change_action = event_changes["action"]
            recordset_changes = event_changes["resourceRecordSet"]

            print_event(event, event_type="** RECORD SET CHANGE **")
            # Force start will override all logic
            if _utils.stop_processing():
                logger.info("HALT_PROCESSING set, not starting jobs.")
                return_status[recordset_changes["name"]] = False
                continue
            if company_domain_filter is not None and not recordset_changes["name"].endswith(company_domain_filter) and not recordset_changes["name"].endswith(
                    f"{company_domain_filter}."):
                logger.warning(
                    f"Not permforming any change because api endpoint is not {company_domain_filter} {recordset_changes['name']}"
                )
                return_status[recordset_changes["name"]] = False
                continue
            if ("setIdentifier" in recordset_changes) and recordset_changes["setIdentifier"] != "Simple":
                logger.warning(
                    f"Not permforming any change because the setIdentifier is not Simple {recordset_changes['name']} {recordset_changes['setIdentifier']}. Typically this is a regional ALB deployment the user needs to handle this!"
                )
                return_status[recordset_changes["name"]] = False
                continue
            response = modify_route53_change_recordset(
                route53_client=dest_route53_client,
                change_action=change_action,
                recordset_name=recordset_changes["name"],
                recordset_type=recordset_changes["type"],
                alias_target_hosted_zone_id=recordset_changes["aliasTarget"]["hostedZoneId"],
                alias_target_dns_name=recordset_changes["aliasTarget"]["dNSName"],
                alias_target_eval_target_health=recordset_changes["aliasTarget"]["evaluateTargetHealth"],
                hosted_zone_id=dest_hosted_zone_id, 
            )
            if response is not None:
                wait_for_recordset_change(route53_client=dest_route53_client, change_id=response["ChangeInfo"]["Id"])
                logger.info(
                    "The change recordset finished completly, but that does not mean that DNS record is propogated to on-prem DNS servers."
                )
            return_status[recordset_changes["name"]] = True
        return return_status
    except Exception as ex:
        raise ex
