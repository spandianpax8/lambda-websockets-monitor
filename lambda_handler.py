import boto3
import copy
import json
import os
import urllib
import urllib3

KEY_PREFIX_WEBSOCKETS = 'URL_WS_'
KEY_PREFIX_WEBSOCKETS_EMITTER = 'URL_WSE_'
KEY_SNS_ARN = 'SNS_ARN'
SNS_ERROR_PAYLOAD_TEMPLATE = { "NewStateValue": "ALARM" }
SNS_WARNING_PAYLOAD_TEMPLATE = { "NewStateValue": "WARNING" }
JSON_HEADER = { 'Content-Type': 'application/json' }
WEBSOCKETS_EMITTER_PAYLOAD_TEMPLATE = { 'environment': None, 'channel': 'app.deployed', 'message': 'now' }

def lambda_handler(event, context):

    sns_client = boto3.client('sns')
    if not sns_client:
        return { 'statusCode': 500, 'body': json.dumps('Unable to create SNS client') }
    
    sns_arn = _get_sns_topic_arn()
    if not sns_arn:
        return { 'statusCode': 404, 'body': json.dumps('Unable to find {0} environment variable'.format(KEY_SNS_ARN)) }

    log = []
    _check_websockets_emitter_instances(sns_client, sns_arn, log)
    _check_websockets_instances(sns_client, sns_arn, log)

    return { 'statusCode': 200, 'body': json.dumps({'Status':'Success', 'Log': log}) }


def _check_websockets_instances(sns_client, sns_arn, log):
    for name, url in _get_urls(KEY_PREFIX_WEBSOCKETS):
        http_code = _get(url)
        log.append({'kind':'Websockets', 'name': name, 'url': url, 'http_code': http_code})
        if http_code != 400:
            message = copy.deepcopy(SNS_ERROR_PAYLOAD_TEMPLATE)
            message['URL'] = url
            message['HTTP_STATUS_CODE'] = http_code
            subject = 'Websockets Down: {0} failed with http status code {1}'.format(name, http_code)
            sns_resp = _publish_alert_to_sns(sns_client, sns_arn, subject, message)

def _check_websockets_emitter_instances(sns_client, sns_arn, log):
    for name, url in _get_urls(KEY_PREFIX_WEBSOCKETS_EMITTER):
        payload = copy.deepcopy(WEBSOCKETS_EMITTER_PAYLOAD_TEMPLATE)
        payload['environment'] = name
        http_code, data = _post_json(url, payload)
        log.append({'kind':'Websockets Emitter', 'name': name, 'url': url, 'http_code': http_code})
        if http_code == 200:
            if data.get('status') == 'published':
                message = copy.deepcopy(SNS_WARNING_PAYLOAD_TEMPLATE)
                message['URL'] = url
                message['PAYLOAD'] = payload
                message['RESPONSE'] = data
                subject = 'Websockets Emitter Issue: {0} returned a non "published" status: {1}'.format(name, data.get('status'))
                sns_resp = _publish_alert_to_sns(sns_client, sns_arn, subject, message)
        else:
            message = copy.deepcopy(SNS_ERROR_PAYLOAD_TEMPLATE)
            message['URL'] = url
            message['HTTP_STATUS_CODE'] = http_code
            subject = 'Websockets Emitter Down: {0} returned a non-200 http status code: {1}'.format(name, http_code)
            sns_resp = _publish_alert_to_sns(sns_client, sns_arn, subject, message)

def _get(url):
    return urllib3.PoolManager().request('GET', url).status

def _post_json(url, payload):
    resp = urllib3.PoolManager().request('POST', url, headers=JSON_HEADER, body=json.dumps(payload))
    return (resp.status, json.loads(resp.data))

def _publish_alert_to_sns(sns_client, sns_arn, subject, message):
    return sns_client.publish(TopicArn = sns_arn, Subject = subject, Message = json.dumps(message))

def _get_sns_topic_arn():
    return os.environ.get(KEY_SNS_ARN)

def _get_urls(url_key_prefix):
    return [(key.replace(url_key_prefix, ''), value) 
            for key, value in os.environ.items() 
            if key.startswith(url_key_prefix)]
