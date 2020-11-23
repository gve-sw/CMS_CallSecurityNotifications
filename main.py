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

# variables
config = yaml.safe_load(open("credentials.yml"))
username = config['username']
password = config['password']
cms_ips = config['cms_ips']
port = config['port']

# globals
meetings_with_message = []
external_participants = []

# Flask app
app = Flask(__name__)

# function to act upon CDR messages
def messaging(record, record_type):

    global meetings_with_message
    global external_participants
    call_id = None

    if record_type == 'callStart':
        # add to DB
        exists = False
        call_correlator = record['call']['callCorrelator']
        call_id = record['call']['@id']
        for meeting in meetings_with_message:
            if meeting['call_correlator'] == call_correlator:
                exists = True
                adding = True
                for call_id_check in meeting['call_ids']:
                    if call_id_check == call_id:
                        adding = False
                if adding == True:
                    meeting['call_ids'].append(call_id)
        if exists == False:
            meeting = {
                'call_correlator': call_correlator,
                'call_ids': [call_id],
                'restricted': False,
                'external_participants': False
            }
            meetings_with_message.append(meeting)

        # check if it is restricted
        call_name = record['call']['name'].lower()
        restricted = 'restricted'
        if restricted in call_name:
            for meeting in meetings_with_message:
                if meeting['call_correlator'] == call_correlator:
                    meeting['restricted'] = True


    elif record_type == 'callLegStart':
        try:
            subType = record['callLeg']['subType']
            if subType == 'webApp':
                call_id = record['callLeg']['call']
                callleg_id = record['callLeg']['@id']

                # get call correlator
                for url in cms_ips:
                    cms_url = 'https://' + url + ':' + port + '/api/v1/calls/' + call_id
                    s = requests.get(cms_url, auth=(username, password), verify=False)
                    if s.status_code == 200:
                        s_text = xmltodict.parse(s.content)
                        call_correlator = s_text['call']['callCorrelator']

                # add participant to list of external participants per call
                p_exists = False
                for participants in external_participants:
                    if participants['call_correlator'] == call_correlator:
                        p_exists = True
                        call = {
                            'callleg_id': callleg_id,
                            'call_id': call_id
                        }
                        participants['calls'].append(call)
                if p_exists == False:
                    external_participant = {
                        'call_correlator': call_correlator,
                        'calls': [
                            {
                                'callleg_id': record['callLeg']['@id'],
                                'call_id': call_id
                            }
                        ]
                    }
                    external_participants.append(external_participant)

                c_exists = False
                for meeting in meetings_with_message:
                    if meeting['call_correlator'] == call_correlator:
                        c_exists = True
                        meeting['external_participants'] = True
                if c_exists == False:
                    meeting = {
                        'call_correlator': call_correlator,
                        'call_ids': [call_id],
                        'restricted': False,
                        'external_participants': True
                    }
                    meetings_with_message.append(meeting)

        except:
            pass

    elif record_type == 'callLegEnd':
        callleg_id = record['callLeg']['@id']
        for participant in external_participants:
            for call in participant['calls']:
                if call['callleg_id'] == callleg_id:
                    call_id = call['call_id']
                    call_correlator = participant['call_correlator']
                    participant['calls'].remove(call)
                    if len(participant['calls']) == 0:
                        for meeting in meetings_with_message:
                            if meeting['call_correlator'] == call_correlator:
                                meeting['external_participants'] = False
                        external_participants.remove(participant)

    elif record_type == 'callEnd':
        call_id_delete = record['call']['@id']
        for meeting in meetings_with_message:
            for call_ids in meeting['call_ids']:
                if call_ids == call_id_delete:
                    meeting['call_ids'].remove(call_id_delete)
            if len(meeting['call_ids']) == 0:
                meetings_with_message.remove(meeting)

    if call_id != None:
        for meeting in meetings_with_message:
            if meeting['call_correlator'] == call_correlator:
                if meeting['restricted'] == True and meeting['external_participants'] == True:
                    payload = 'messageText=Restricted%20Meeting,%20External%20Participant(s)%20in%20Meeting&messagePosition=bottom&messageDuration=permanent'
                elif meeting['restricted'] == True and meeting['external_participants'] == False:
                    payload = 'messageText=Restricted%20Meeting&messagePosition=bottom&messageDuration=permanent'
                elif meeting['restricted'] == False and meeting['external_participants'] == True:
                    payload = 'messageText=External%20Participant(s)%20in%20Meeting&messagePosition=bottom&messageDuration=permanent'
                elif meeting['restricted'] == False and meeting['external_participants'] == False:
                    payload = 'messageText=&messagePosition=bottom&messageDuration=0'

        for url in cms_ips:
            cms_url = 'https://' + url + ':' + port + '/api/v1/calls/' + call_id
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            requests.put(cms_url, auth=(username, password), headers=headers, data=payload, verify=False)


# CDR listener
@app.route('/cdr', methods=['POST'])
def post():

    try:
        cdr = xmltodict.parse(request.data)
        if isinstance(cdr['records']['record'], list):
            for record in cdr['records']['record']:
                record_type = record['@type']
                if record_type == 'callStart' or 'callLegStart' or 'callEnd' or 'callLegEnd':
                    messaging(record, record_type)
        else:
            record = cdr['records']['record']
            record_type = record['@type']
            if record_type == 'callStart' or 'callLegStart' or 'callEnd' or 'callLegEnd':
                messaging(record, record_type)
        return('', 204)

    except Exception as e:
        print(e)
        return('', 204)


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
