#!/usr/bin/env python

# Copyright (C) 2018 by eHealth Africa : http://www.eHealthAfrica.org
#
# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import requests

from . import *  # noqa
from aet.kafka import KafkaConsumer

# Test Suite contains both unit and integration tests
# Unit tests can be run on their own from the root directory
# enter the bash environment for the version of python you want to test
# for example for python 3
# `docker-compose run consumer-sdk-test bash`
# then start the unit tests with
# `pytest -m unit`
# to run integration tests / all tests run the test_all.sh script from the /tests directory.


#####################
# Integration Tests #
#####################

@pytest.mark.integration
def test_read_messages_no_schema(messages_test_no_schema, default_consumer_args):
    _ids = [m['id'] for m in messages_test_no_schema]
    topic = "TestPlainMessages"
    assert(len(messages_test_no_schema) ==
           topic_size), "Should have generated the right number of messages"
    iter_consumer = KafkaConsumer(**default_consumer_args)
    iter_consumer.subscribe(topic)
    iter_consumer.seek_to_beginning()
    # more than a few hundres is too large to grab in one pass when not serialized
    for x in range(int(3 * topic_size / 500)):
        messages = iter_consumer.poll_and_deserialize(timeout_ms=10000, max_records=1000)
        # read messages and check masking
        for partition, packages in messages.items():
            for package in packages:
                for msg in package.get("messages"):
                    _id = msg.get('id')
                    try:
                        # remove found records from our pick list
                        _ids.remove(_id)
                    except ValueError:
                        # record may be in another batch
                        pass
        if len(_ids) == 0:
            break
    iter_consumer.close()
    # make sure we read all the records
    assert(len(_ids) == 0)


@pytest.mark.integration
@pytest.mark.parametrize("emit_level,unmasked_fields", [
    (0, 2),
    (1, 3),
    (2, 4),
    (3, 5),
    (4, 6),
    (5, 7),
])
def test_masking_boolean_pass(default_consumer_args,
                              messages_test_boolean_pass,
                              emit_level,
                              unmasked_fields):
    topic = "TestBooleanPass"
    assert(len(messages_test_boolean_pass) ==
           topic_size), "Should have generated the right number of messages"
    # set configs
    consumer_kwargs = default_consumer_args
    consumer_kwargs["aether_masking_schema_emit_level"] = emit_level
    # get messages for this emit level
    iter_consumer = KafkaConsumer(**consumer_kwargs)
    iter_consumer.subscribe(topic)
    iter_consumer.seek_to_beginning()
    messages = iter_consumer.poll_and_deserialize(timeout_ms=10000, max_records=1000)
    iter_consumer.close()
    # read messages and check masking
    for partition, packages in messages.items():
        for package in packages:
            for msg in package.get("messages"):
                assert(len(msg.keys()) ==
                       unmasked_fields), "%s fields should be unmasked" % unmasked_fields


@pytest.mark.integration
@pytest.mark.parametrize("emit_level,unmasked_fields", [
    ("uncategorized", 2),
    ("public", 3),
    ("confidential", 4),
    ("secret", 5),
    ("top secret", 6),
    ("ufos", 7),
])
@pytest.mark.parametrize("masking_taxonomy", [
    (["public", "confidential", "secret", "top secret", "ufos"])
])
def test_masking_category_pass(default_consumer_args,
                               messages_test_secret_pass,
                               emit_level,
                               masking_taxonomy,
                               unmasked_fields):
    topic = "TestTopSecret"
    assert(len(messages_test_secret_pass) ==
           topic_size), "Should have generated the right number of messages"
    # set configs
    consumer_kwargs = default_consumer_args
    consumer_kwargs["aether_masking_schema_emit_level"] = emit_level
    consumer_kwargs["aether_masking_schema_levels"] = masking_taxonomy
    # get messages for this emit level
    iter_consumer = KafkaConsumer(**consumer_kwargs)
    iter_consumer.subscribe(topic)
    iter_consumer.seek_to_beginning()
    messages = iter_consumer.poll_and_deserialize(timeout_ms=10000, max_records=1000)
    iter_consumer.close()
    # read messages and check masking
    for partition, packages in messages.items():
        for package in packages:
            for msg in package.get("messages"):
                assert(len(msg.keys()) ==
                       unmasked_fields), "%s fields should be unmasked" % unmasked_fields


@pytest.mark.integration
@pytest.mark.parametrize("required_field, publish_on, expected_count", [
    (True, [True], int(topic_size / 2)),
    (True, [False], int(topic_size / 2)),
    (True, [True, False], topic_size),
    (True, True, int(topic_size / 2)),
    (True, False, int(topic_size / 2)),
    (False, True, int(topic_size))  # Turn off publish filtering
])
def test_publishing_boolean_pass(default_consumer_args,
                                 messages_test_boolean_pass,
                                 required_field,
                                 publish_on,
                                 expected_count):
    topic = "TestBooleanPass"
    assert(len(messages_test_boolean_pass) ==
           topic_size), "Should have generated the right number of messages"
    # set configs
    consumer_kwargs = default_consumer_args
    consumer_kwargs["aether_emit_flag_required"] = required_field
    consumer_kwargs["aether_emit_flag_values"] = publish_on
    # get messages for this emit level
    iter_consumer = KafkaConsumer(**consumer_kwargs)
    iter_consumer.subscribe(topic)
    iter_consumer.seek_to_beginning()
    messages = iter_consumer.poll_and_deserialize(timeout_ms=10000, max_records=1000)
    iter_consumer.close()
    # read messages and check masking
    count = 0
    for partition, packages in messages.items():
        for package in packages:
            for msg in package.get("messages"):
                count += 1
    assert(count == expected_count), "unexpected # of messages published"


@pytest.mark.integration
@pytest.mark.parametrize("publish_on, expected_values", [
    (["yes"], ["yes"]),
    (["yes", "maybe"], ["yes", "maybe"]),
    ("yes", ["yes"])
])
def test_publishing_enum_pass(default_consumer_args,
                              messages_test_enum_pass,
                              publish_on,
                              expected_values):
    topic = "TestEnumPass"
    assert(len(messages_test_enum_pass) ==
           topic_size), "Should have generated the right number of messages"
    # set configs
    consumer_kwargs = default_consumer_args
    consumer_kwargs["aether_emit_flag_values"] = publish_on
    # get messages for this emit level
    iter_consumer = KafkaConsumer(**consumer_kwargs)
    iter_consumer.subscribe(topic)
    iter_consumer.seek_to_beginning()
    messages = iter_consumer.poll_and_deserialize(timeout_ms=10000, max_records=1000)
    iter_consumer.close()
    # read messages and check masking
    for partition, packages in messages.items():
        for package in packages:
            for msg in package.get("messages"):
                assert(msg.get("publish") in expected_values)

#####################
#    Unit Tests     #
#####################

######
#
#  KAFKA Consumer
#
#####


@pytest.mark.unit
@pytest.mark.parametrize("field_path,field_value,pass_msg,fail_msg", [
    (None, None, {"approved": True}, {"approved": False}),
    ("$.checked", None, {"checked": True}, {"checked": False}),
    (None, [False], {"approved": False}, {"approved": True}),
    (None, ["yes", "maybe"], {"approved": "yes"}, {"approved": "no"}),
    (None, ["yes", "maybe"], {"approved": "maybe"}, {"approved": "no"}),
    (None, ["yes", "maybe"], {"approved": "maybe"}, {"checked": "maybe"})
])
def test_get_approval_filter(offline_consumer, field_path, field_value, pass_msg, fail_msg):
    if field_path:
        offline_consumer._add_config({"aether_emit_flag_field_path": field_path})
    if field_value:
        offline_consumer._add_config({"aether_emit_flag_values": field_value})
    _filter = offline_consumer.get_approval_filter()
    assert(_filter(pass_msg))
    assert(_filter(fail_msg) is not True)


@pytest.mark.unit
@pytest.mark.parametrize("emit_level", [
    (0),
    (1),
    (2),
    (3),
    (4),
    (5)
])
@pytest.mark.unit
def test_msk_msg_default_map(offline_consumer, sample_schema, sample_message, emit_level):
    offline_consumer._add_config({"aether_masking_schema_emit_level": emit_level})
    mask = offline_consumer.get_mask_from_schema(sample_schema)
    masked = mask(sample_message)
    assert(len(masked.keys()) == (emit_level + 2)), ("%s %s" % (emit_level, masked))


@pytest.mark.unit
@pytest.mark.parametrize("emit_level,expected_count", [
    ("no matching taxonomy", 2),
    ("public", 3),
    ("confidential", 4),
    ("secret", 5),
    ("top secret", 6),
    ("ufos", 7)
])
@pytest.mark.parametrize("possible_levels", [([  # Single parameter for all tests
    "public",
    "confidential",
    "secret",
    "top secret",
    "ufos"
])])
def test_msk_msg_custom_map(offline_consumer,
                            sample_schema_top_secret,
                            sample_message_top_secret,
                            emit_level,
                            possible_levels,
                            expected_count):
    offline_consumer._add_config({"aether_masking_schema_emit_level": emit_level})
    offline_consumer._add_config({"aether_masking_schema_levels": possible_levels})
    mask = offline_consumer.get_mask_from_schema(sample_schema_top_secret)
    masked = mask(sample_message_top_secret)
    assert(len(masked.keys()) == (expected_count)), ("%s %s" % (emit_level, masked))


######
#
#  API TESTS
#
#####

@pytest.mark.unit
@pytest.mark.parametrize("call,result", [
                        ('jobs/delete', True),
                        ('jobs/get', {}),
                        ('jobs/list', {}),
                        ('healthcheck', 'healthy')
])
def test_api_get_calls(call, result, mocked_api):
    user = settings.CONSUMER_CONFIG.get('ADMIN_USER')
    pw = settings.CONSUMER_CONFIG.get('ADMIN_PW')
    auth = requests.auth.HTTPBasicAuth(user, pw)
    port = settings.CONSUMER_CONFIG.get('EXPOSE_PORT')
    url = f'http://localhost:{port}/{call}'
    res = requests.get(url, auth=auth)
    res.raise_for_status()
    try:
        val = res.json()
    except json.decoder.JSONDecodeError:
        val = res.text
    finally:
        assert(val == result)


@pytest.mark.unit
@pytest.mark.parametrize("call,result,body", [
                        ('jobs/add', False, {'a': 'b'}),
                        ('jobs/update', False, {'a': 'b'}),
                        ('jobs/add', True, {}),
                        ('jobs/update', True, {})
])
def test_api_post_calls(call, result, body, mocked_api):
    user = settings.CONSUMER_CONFIG.get('ADMIN_USER')
    pw = settings.CONSUMER_CONFIG.get('ADMIN_PW')
    auth = requests.auth.HTTPBasicAuth(user, pw)
    port = settings.CONSUMER_CONFIG.get('EXPOSE_PORT')
    url = f'http://localhost:{port}/{call}'
    res = requests.post(url, auth=auth, json=body)
    res.raise_for_status()
    try:
        val = res.json()
    except json.decoder.JSONDecodeError:
        val = res.text
    finally:
        assert(val == result), f'{call} | {result} | {body}'


######
#
#  CONSUMER TESTS
#
#####


@pytest.mark.unit
def test_load_schema_validate(mocked_consumer):
    c = mocked_consumer
    permissive = c.load_schema('/code/conf/schema/permissive.json')
    strict = c.load_schema('/code/conf/schema/strict.json')
    job = {'a': 1}
    assert(c.validate_job(job, permissive) is True)
    assert(c.validate_job(job, strict) is False)


######
#
#  TASK TESTS
#
#####


@pytest.mark.integration
@pytest.mark.parametrize("name,args,expected", [
                        ('remove', ['00001', 'test'], False),
                        ('exists', ['00001', 'test'], False),
                        ('add', [{'id': '00001'}, 'test'], True),
                        ('exists', ['00001', 'test'], True),
                        ('remove', ['00001', 'test'], True),
                        ('exists', ['00001', 'test'], False)
])
def test_redis_io(name, args, expected, task_helper):
    fn = getattr(task_helper, name)
    res = fn(*args)
    assert(res == expected)


@pytest.mark.integration
def test_redis_get_methods(task_helper):
    tasks = [
        {'id': '00001', 'a': 1},
        {'id': '00002', 'a': 2},
    ]
    _type = 'test'
    for t in tasks:
        assert(task_helper.add(t, _type) is True)
        assert(task_helper.exists(t['id'], _type) is True)
    for t in tasks:
        _id = t['id']
        from_redis = task_helper.get(_id, _type)
        assert(from_redis.get('id') == _id)
    try:
        task_helper.get('fake_id', _type)
    except ValueError:
        pass
    else:
        assert(False)
    redis_ids = list(task_helper.list(_type))
    assert(all([t['id'] in redis_ids for t in tasks]))
