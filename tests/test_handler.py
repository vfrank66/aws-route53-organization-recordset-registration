import json
import os

import moto
import pytest
from more_itertools import side_effect

import message_processing
from handler import lambda_handler

from . import test_constants


class TestHandler:
    """Test class for handler."""
    def test_handler_good_create_event(
        self,
        context,
        route53_client,
        sts_client,
        create_recordset_event,
        delete_recordset_event,
    ):
        """Test we fail on Lambda handler error value."""
        response = lambda_handler(create_recordset_event, context)
        assert len(response) == 1
        assert list(response.items())[0][1] is True
        response = lambda_handler(delete_recordset_event, context)
        assert len(response) == 1
        assert list(response.items())[0][1] is True

    def test_handler_duplicate_create_resource_exit_success(self, context, mocker, route53_client, sts_client,
                                                            create_recordset_event):
        """Test we fail on Lambda handler error value."""
        mocker.patch(
            "message_processing.change_resource_record_sets",
            side_effect=[
                route53_client.exceptions.InvalidChangeBatch(
                    operation_name="change_resource_record_sets",
                    error_response={
                        "Error": {
                            "Message":
                            "[Tried to create resource record set [name='test.api.test.io.', type='A', set-identifier='Simple'] but it already exists]"
                        }
                    },
                ),
                {
                    "ChangeInfo": {
                        "Id": "unit-testing"
                    }
                },
            ],
        )
        response = lambda_handler(create_recordset_event, context)
        assert len(response) == 1
        assert list(response.items())[0][1] is True

    def test_handler_delete_when_record_does_not_exist_safetly_exit_success(self, context, mocker, route53_client,
                                                                            sts_client, create_recordset_event):
        """Test we fail on Lambda handler error value."""
        mocker.patch(
            "message_processing.change_resource_record_sets",
            side_effect=[
                route53_client.exceptions.InvalidChangeBatch(
                    operation_name="change_resource_record_sets",
                    error_response={
                        "Error": {
                            "Message":
                            "[Tried to delete resource record set [name='test.api.test.io.', type='A', set-identifier='Simple'] but it was not found]"
                        }
                    },
                )
            ],
        )
        response = lambda_handler(create_recordset_event, context)
        assert len(response) == 1
        assert list(response.items())[0][1] is True

    def test_handler_delete_resource_that_does_not_exist(self, context, route53_client, sts_client,
                                                         delete_recordset_event):
        """Test we fail on Lambda handler error value."""
        response = lambda_handler(delete_recordset_event, context)

        assert len(response) == 1
        assert list(response.items())[0][1] is True

    def test_handler_stop_processing_halt_processing_flag(self, context, mocker, route53_client, sts_client,
                                                          create_recordset_event):
        """Test we fail on Lambda handler error value."""
        os.environ["HALT_PROCESSING"] = "1"
        route53_change_recordset_spy = mocker.spy(message_processing, "modify_route53_change_recordset")

        response = lambda_handler(create_recordset_event, context)

        assert len(response) == 1
        assert list(response.items())[0][1] is False
        assert route53_change_recordset_spy.call_count == 0

    def test_handler_stop_processing_not_company_filter_domain(self, context, mocker, route53_client, sts_client,
                                                               create_recordset_event):
        """Test we igonre recordset notification because it is not a
        api.test.io domain."""
        create_recordset_event["detail"]["requestParameters"]["changeBatch"]["changes"][0]["resourceRecordSet"][
            "name"] = "test-url.not.an.api"
        route53_change_recordset_spy = mocker.spy(message_processing, "modify_route53_change_recordset")
        response = lambda_handler(create_recordset_event, context)
        assert len(response) == 1
        assert list(response.items())[0][1] is False

    def test_handler_stop_processing_external_recordset(self, context, mocker, route53_client, sts_client,
                                                        bad_create_recordset_event):
        """Test ignore to process a known external domain."""
        route53_change_recordset_spy = mocker.spy(message_processing, "modify_route53_change_recordset")
        response = lambda_handler(bad_create_recordset_event, context)
        assert len(response) == 2
        assert list(response.items())[0][1] is False

    def test_handler_stop_processing_regional_deployment(self, context, mocker, route53_client, sts_client,
                                                         regional_alb_recordset_event):
        """Test we fail on Lambda handler error value."""
        route53_change_recordset_spy = mocker.spy(message_processing, "modify_route53_change_recordset")
        response = lambda_handler(regional_alb_recordset_event, context)
        assert len(response) == 1
        assert list(response.items())[0][1] is False

    def test_handler_handle_error(
        self,
        context,
        route53_client,
        sts_client,
    ):
        """Test we fail on bad event."""
        with pytest.raises(Exception) as ex:
            lambda_handler("i am a broken event", context)
        assert ex.typename == "TypeError"
