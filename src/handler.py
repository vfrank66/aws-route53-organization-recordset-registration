"""Main Lambda handler."""
import json
import logging
import os
import sys
import traceback

import message_processing

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Lambda main handler."""
    try:
        return message_processing.process_message(event, context)
    except Exception as e:
        logger.info(event)
        logger.error(f"Lambda ERROR aws-route53-organization-recordset-registration: \n {e}")
        traceback.print_exc(file=sys.stdout)
        exception_type = e.__class__.__name__
        exception_message = str(e)
        api_exception_obj = {"isError": True, "type": exception_type, "message": exception_message}
        logger.error(json.dumps(api_exception_obj))
        raise e


if __name__ == "__main__":
    event_type = "create"  # "create", "delete", "update"
    if event_type == "create":
        event_data = open(os.path.join(os.getcwd(), "./tests/test-files/eventbridge.create.event.json"))
        json_event = json.load(event_data)
    elif event_type == "delete":
        event_data = open(os.path.join(os.getcwd(), "./tests/test-files/eventbridge.delete.event.json"))
        json_event = json.load(event_data)
    # elif event_type == "update":
    #     event_data = open(os.path.join(os.getcwd(), "./tests/test-files/eventbridge.update.event.json"))
    #     json_event = json.load(event_data)
    else:
        raise Exception("Unable to run locally, invalid event type.")
    lambda_handler(json_event, "handler")
