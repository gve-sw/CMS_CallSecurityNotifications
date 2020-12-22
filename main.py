'''
Copyright (c) 2020 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
'''

from flask import Flask, request, redirect, jsonify
import xmltodict, requests, yaml
import logging, logging.handlers, datetime

# variables
config = yaml.safe_load(open("credentials.yml"))
username = config['username']
password = config['password']
cms_ips = config['cms_ips']
port = config['port']
internal_domains = config['internal_domains']
secure_domains = config['secure_domains']

# globals
meetings_with_message = []
participants_db = []

# Flask app
app = Flask(__name__)

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# f_handler = logging.handlers.TimedRotatingFileHandler('app.log', when='W0', backupCount = 5)
f_handler = logging.FileHandler('app.log')
f_handler.setLevel(logging.DEBUG)
f_format = logging.Formatter('%(asctime)s - %(message)s')
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)


#function to add and classify participants in meeting dict, and if external to participants_db
def new_participant(call_correlator, call_id, callleg_id, success_cms, connection):

    global participants_db
    global meetings_with_message

    # add participant to list of external participants per call
    if connection == 'external':
        p_exists = False
        for participants in participants_db:
            if participants['call_correlator'] == call_correlator:
                p_exists = True

                cid_exists = False
                for callleg in participants['calls']:
                    if callleg['callleg_id'] == callleg_id:
                        cid_exists = True
                if cid_exists == False:
                    call = {
                        'callleg_id': callleg_id,
                        'call_id': call_id
                    }
                    participants['calls'].append(call)

        if p_exists == False:
            participant = {
                'call_correlator': call_correlator,
                'calls': [
                    {
                        'callleg_id': callleg_id,
                        'call_id': call_id
                    }
                ]
            }
            participants_db.append(participant)

    # add participant to meeting dict
    add_participant_to_meeting(call_correlator, call_id, callleg_id, success_cms)

    # add callleg_id to list of connections, per type, in meeting dict
    for meeting in meetings_with_message:
        if meeting['call_correlator'] == call_correlator:
            if connection == 'secure':
                exists = False
                for callleg_secure in meeting['secure_participant']:
                    if callleg_secure == callleg_id:
                        exists = True
                        break
                if exists == False:
                    meeting['secure_participant'].append(callleg_id)
            elif connection == 'internal':
                exists = False
                for callleg_internal in meeting['internal_participant']:
                    if callleg_internal == callleg_id:
                        exists = True
                        break
                if exists == False:
                    meeting['internal_participant'].append(callleg_id)
            elif connection == 'external':
                exists = False
                for callleg_external in meeting['external_participant']:
                    if callleg_external == callleg_id:
                        exists = True
                        break
                if exists == False:
                    meeting['external_participant'].append(callleg_id)

    return meetings_with_message


# function to add participants to meeting dict
def add_participant_to_meeting(call_correlator, call_id, callleg_id, success_cms):

    global meetings_with_message

    add_meeting_result = add_meeting(call_correlator, call_id, success_cms)
    update = add_meeting_result[1]

    for meeting in meetings_with_message:
        if meeting['call_correlator'] == call_correlator:
            adding = True
            for call_id_check in meeting['call_ids']:
                if call_id_check['call_id'] == call_id:
                    adding = False

                    callleg_id_exists = False
                    for calllegs in call_id_check['calllegs']:
                        if calllegs == callleg_id:
                            callleg_id_exists = True
                            break
                    if callleg_id_exists == False:
                        call_id_check['calllegs'].append(callleg_id)

                    if call_id_check['success_cms'] == None:
                        call_id_check['success_cms'] = success_cms

                    break

            if adding == True:
                new = {
                    'call_id': call_id,
                    'success_cms': success_cms,
                    'calllegs': [callleg_id]
                }
                meeting['call_ids'].append(new)

    return meetings_with_message, update


# function to add meeting to meeting dict
def add_meeting(call_correlator, call_id, success_cms):

    update = False

    exists = False
    for meeting in meetings_with_message:
        if meeting['call_correlator'] == call_correlator:
            exists = True

            adding = True
            for call_id_check in meeting['call_ids']:
                if call_id_check['call_id'] == call_id:
                    adding = False

            if adding == True:
                new = {
                    'call_id': call_id,
                    'success_cms': success_cms,
                    'calllegs': []
                }
                meeting['call_ids'].append(new)

    if exists == False:
        update = True
        meeting = {
            'call_correlator': call_correlator,
            'call_ids': [
                {
                    'call_id': call_id,
                    'success_cms': success_cms,
                    'calllegs': []
                }
            ],
            'secure_participant': [],
            'internal_participant': [],
            'external_participant': []
        }
        meetings_with_message.append(meeting)

    return meetings_with_message, update


# function to get call_correlator
def get_call_correlator(call_id, callleg_id):

    cms = None

    if call_id == None:
        for url in cms_ips:
            cms_url = 'https://' + url + ':' + port + '/api/v1/calllegs/' + callleg_id
            r = requests.get(cms_url, auth=(username, password), verify=False)
            if r.status_code == 200:
                cms = url
                r_text = xmltodict.parse(r.content)
                call_id = r_text['callLeg']['call']
                break

    if cms != None:
        cms_url = 'https://' + cms + ':' + port + '/api/v1/calls/' + call_id
        s = requests.get(cms_url, auth=(username, password), verify=False)
        if s.status_code == 200:
            success_cms = url
            s_text = xmltodict.parse(s.content)
            call_correlator = s_text['call']['callCorrelator']
    else:
        for url in cms_ips:
            cms_url = 'https://' + url + ':' + port + '/api/v1/calls/' + call_id
            s = requests.get(cms_url, auth=(username, password), verify=False)
            if s.status_code == 200:
                success_cms = url
                s_text = xmltodict.parse(s.content)
                call_correlator = s_text['call']['callCorrelator']
                break

    print('result get call correlator: ' + str(success_cms) + ' ' + str(call_correlator) + ' ' + str(call_id))

    return success_cms, call_correlator, call_id


# process CDR messages depending on record type
def messaging(record, record_type):

    print(record)

    global meetings_with_message
    global participants_db
    update = False
    call_correlator = None
    call_id = None
    success_cms = None

    print("meetings_with_message before: "+ str(meetings_with_message))
    print("participants_db before: "+ str(participants_db))


    # for 'callStart' CDR type, adding meetings to meeting dict
    if record_type == 'callStart':

        call_correlator = record['call']['callCorrelator']
        call_id = record['call']['@id']

        add_meeting_result = add_meeting(call_correlator, call_id, success_cms)
        update = add_meeting_result[1]

        logger.debug('call started, call correlator: ' + str(call_correlator))

        print('end callStart method')


    # for 'callLegStart' CDR type, identifying webRTC connections and adding participants to meeting dict
    elif record_type == 'callLegStart':

        try:
            subType = record['callLeg']['subType']
            if subType == 'webApp':

                connection = 'external'
                call_id = record['callLeg']['call']
                callleg_id = record['callLeg']['@id']

                get_call_correlator_result = get_call_correlator(call_id, callleg_id)
                success_cms = get_call_correlator_result[0]
                call_correlator = get_call_correlator_result[1]

                new_participant(call_correlator, call_id, callleg_id, success_cms, connection)
                update = True

                logger.debug('external participant with callleg_id ' + str(callleg_id) + ' joined call with call_correlator ' + str(call_correlator) + ', joined via Web App')

        except:
            call_id = None
            callleg_id = record['callLeg']['@id']

            get_call_correlator_result = get_call_correlator(call_id, callleg_id)
            success_cms = get_call_correlator_result[0]
            call_correlator = get_call_correlator_result[1]
            call_id = get_call_correlator_result[2]

            add_participant_to_meeting_result = add_participant_to_meeting(call_correlator, call_id, callleg_id, success_cms)
            update = add_participant_to_meeting_result[1]

        print('end callLegStart method')


    # for 'callLegUpdate' CDR type, identifying SIP call connections and classifying them as secure, internal or external
    elif record_type == 'callLegUpdate':

        try:
            sipCallId = record['callLeg']['sipCallId']

            callleg_id = record['callLeg']['@id']
            for meeting in meetings_with_message:
                for call_id_list in meeting['call_ids']:
                    for callleg_list in call_id_list['calllegs']:
                        if callleg_id == callleg_list:
                            call_correlator = meeting['call_correlator']
                            call_id = call_id_list['call_id']
                            success_cms = call_id_list['success_cms']

            ''' 
            try:
                call_id = record['callLeg']['call']
            except:
                call_id = None
            '''

            remoteAddress = record['callLeg']['remoteAddress']
            internal_identifier = remoteAddress.lower()

            # check against secure domains list
            j = 0
            for secure_domain in secure_domains:
                compare_secure_domain = secure_domain.lower()
                if compare_secure_domain in internal_identifier:
                    j = +1
                    break
            if j == 1:
                connection = 'secure'
                if call_id == None:
                    get_call_correlator_result = get_call_correlator(call_id, callleg_id)
                    success_cms = get_call_correlator_result[0]
                    call_correlator = get_call_correlator_result[1]
                    call_id = get_call_correlator_result[2]

                new_participant(call_correlator, call_id, callleg_id, success_cms, connection)
                update = True

                logger.debug('participant from secure domain list with callleg_id ' + str(callleg_id) + ' joined call with call_correlator ' + str(call_correlator))

            else: # check against internal domains list, provided it was not part of a secure domain
                i = 0
                for internal_domain in internal_domains:
                    compare_internal_domain = internal_domain.lower()
                    if compare_internal_domain in internal_identifier:
                        i =+1
                        break
                if i == 1:
                    connection = 'internal'
                else: # if the domain is not listed in the internal domains list, it is classified as external connection
                    connection = 'external'

                if call_id == None:
                    get_call_correlator_result = get_call_correlator(call_id, callleg_id)
                    success_cms = get_call_correlator_result[0]
                    call_correlator = get_call_correlator_result[1]
                    call_id = get_call_correlator_result[2]

                new_participant(call_correlator, call_id, callleg_id, success_cms, connection)
                update = True

                if connection == 'internal':
                    logger.debug('internal participant with callleg_id ' + str(callleg_id) + ' joined call with call_correlator ' + str(call_correlator))
                else:
                    logger.debug('external participant with callleg_id ' + str(callleg_id) + ' joined call with call_correlator ' + str(call_correlator) + ', joined via external Jabber')

        except:
            pass

        print('end callLegUpdate method')


    # for 'callLegEnd' CDR type, deleting callleg out of the participants and meetings dict
    elif record_type == 'callLegEnd':

        callleg_id = record['callLeg']['@id']

        for participant in participants_db:
            for call in participant['calls']:
                if call['callleg_id'] == callleg_id:
                    call_id = call['call_id']
                    call_correlator = participant['call_correlator']
                    participant['calls'].remove(call)

                    if len(participant['calls']) == 0:
                        participants_db.remove(participant)

        for meeting in meetings_with_message:
            current_meeting = False
            for call_ids in meeting['call_ids']:
                for calllegs in call_ids['calllegs']:
                    if calllegs == callleg_id:
                        current_meeting = True
                        call_ids['calllegs'].remove(callleg_id)
                        break
            if current_meeting == True:
                call_correlator = meeting['call_correlator']
                for p in meeting['secure_participant']:
                    if p == callleg_id:
                        meeting['secure_participant'].remove(p)
                        if len(meeting['secure_participant']) == 0:
                            update = True
                        logger.debug('participant from secure domain list with callleg_id ' + str(callleg_id) + ' left call with call_correlator ' + str(call_correlator))
                for p in meeting['internal_participant']:
                    if p == callleg_id:
                        meeting['internal_participant'].remove(p)
                        if len(meeting['internal_participant']) == 0:
                            update = True
                        logger.debug('internal participant with callleg_id ' + str(callleg_id) + ' left call with call_correlator ' + str(call_correlator))
                for p in meeting['external_participant']:
                    if p == callleg_id:
                        meeting['external_participant'].remove(p)
                        if len(meeting['external_participant']) == 0:
                            update = True
                        logger.debug('external participant with callleg_id ' + str(callleg_id) + ' left call with call_correlator ' + str(call_correlator))

        print('end callLegEnd method')


    # for 'callEnd' CDR type, deleting the call out of the meetings dict
    elif record_type == 'callEnd':

        call_id_delete = record['call']['@id']
        for meeting in meetings_with_message:
            for call_ids in meeting['call_ids']:
                if call_ids['call_id'] == call_id_delete:

                    if len(call_ids['calllegs']) == 0:
                        call_correlator = meeting['call_correlator']
                        meeting['call_ids'].remove(call_ids)

                    if len(meeting['call_ids']) == 0:
                        meetings_with_message.remove(meeting)
                        logger.debug('call ended, call correlator: ' + str(call_correlator))

        print('end callEnd method')


    if update: # if something was changed impacting the message shown in a call, the message gets updated

        for meeting in meetings_with_message:
            if meeting['call_correlator'] == call_correlator: # find the right meeting info in the dict
                # find a valid call_id
                for meeting_call in meeting['call_ids']:
                    if len(meeting_call['calllegs']) != 0:
                        call_id = meeting_call['call_id']

                # define the payload depending on the information in the participants lists per connection type in the meeting dict
                payload = ''
                if len(meeting['external_participant']) != 0:
                    payload = 'messageText=Security%20Level%203&messagePosition=bottom&messageDuration=permanent'
                    message_text = 'Security Level 3'
                elif len(meeting['internal_participant']) != 0:
                    payload = 'messageText=Security%20Level%202&messagePosition=bottom&messageDuration=permanent'
                    message_text = 'Security Level 2'
                elif len(meeting['secure_participant']) != 0:
                    payload = 'messageText=Security%20Level%201&messagePosition=bottom&messageDuration=permanent'
                    message_text = 'Security Level 1'

                # API call
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                if payload != '':
                    print('updating')

                    # to check if a CMS instance is already defined, to make less API calls
                    known_cms = False
                    for call in meeting['call_ids']:
                        if call['call_id'] == call_id:
                            url = call['success_cms']
                            if url != None:
                                known_cms = True
                                cms_url = 'https://' + url + ':' + port + '/api/v1/calls/' + call_id
                                r = requests.put(cms_url, auth=(username, password), headers=headers, data=payload, verify=False)
                                if r.status_code == 200:
                                    logger.debug('call notification in call with call correlator ' + str(call_correlator) + ' updated to ' + message_text)
                                else:
                                    known_cms = False
                                break

                    # if no CMS instance is defined or the previous call was not successful
                    if known_cms == False:
                        for url in cms_ips:
                            cms_url = 'https://' + url + ':' + port + '/api/v1/calls/' + call_id
                            p = requests.put(cms_url, auth=(username, password), headers=headers, data=payload, verify=False)
                            if p.status_code == 200:
                                logger.debug('call notification in call with call correlator ' + str(call_correlator) + ' updated to ' + message_text)

                                for call in meeting['call_ids']:
                                    if call['call_id'] == call_id:
                                        call['success_cms'] = url

                                break

    print("meetings_with_message after: " + str(meetings_with_message))
    print("participants_db after: " + str(participants_db))


# CDR listener
@app.route('/cdr', methods=['POST'])
def post():

    try:
        cdr = xmltodict.parse(request.data)
        if isinstance(cdr['records']['record'], list): # CDRs can be sent in lists or as single CDR, requiring different handling
            for record in cdr['records']['record']:
                record_type = record['@type']
                # filter for only the CDRs needed
                if record_type == 'callStart' or 'callLegStart' or 'callEnd' or 'callLegEnd':
                    messaging(record, record_type)
        else:
            record = cdr['records']['record']
            record_type = record['@type']
            # filter for only the CDRs needed
            if record_type == 'callStart' or 'callLegStart' or 'callEnd' or 'callLegEnd':
                messaging(record, record_type)
        return('', 204)

    except Exception as e:
        print(e)
        return('', 204)


# run app
if __name__ == '__main__':
    logger.debug('app starting')
    app.debug = True
    app.run(host='0.0.0.0')
