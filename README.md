# Cisco Meeting Server Call Security Notifications

An application to notify participants in a CMS call about different security levels depending on whether external participants are in the call or not ([watch demo](https://youtu.be/2dv9xmZRmXs)).

## Overview
 
![High Level Workflow](IMAGES/workflow.png)

**Cisco Meeting Server**: The [CMS](https://developer.cisco.com/cisco-meeting-server/) brings premises-based video, audio, and web communication together to meet the collaboration needs of the modern workplace. Through the use of its APIs, calls and conferences can be flexibly managed and integrated into existing business workflows. This application focuses on notifying call participants about the security level of the respective call, depending on whether internal or external participants are in the call. Notifications are shown following this logic, always giving priority to the highest applicable level: 
* **Security Level 1**: if participants are joining via SIP coming from a domain listed as *secure_domain* (see `credentials.yml` file and [Installation](#Installation) below), could be used for endpoints located on-prem 
* **Security Level 2**': if participants are joining via SIP coming from a domain listed as *internal_domain* (see `credentials.yml` file and [Installation](#Installation) below), could be used for employees connecting via Jabber 
* **Security Level 3**: if participants are joining via WebRTC or SIP from an unknown domain (i.e. a domain NOT listed as *secure_domain* or *internal_domain*), used for externals

**Call Detail Records**: The CMS generates [Call Detail Records](https://www.cisco.com/c/dam/en/us/td/docs/conferencing/ciscoMeetingServer/Reference_Guides/Version-2-9/Cisco-Meeting-Server-CDR-Guide-2-9.pdf) (CDRs) internally for call-related events, such as a new call starting or a participant joining a call. These CDRs can be sent out by the CMS over HTTP or HTTPS as a series of XML documents to a receiving web server. In this prototype, the CDRs are sent to the Flask application that uses the incoming information to display the updated security level notifications in the respective calls in real-time as described above.

**Flask**: The application is written in Python using the micro web framework Flask. The web server that is part of Flask should not be used in production.

**Logging**: The application logs call information, incl. which security levels are shown in which calls, to the `app.log` file. 



## Contacts
* Jara Osterfeld (josterfe@cisco.com)



## Solution Components
* Cisco Meeting Server, incl. Call Details Records and its API
* Python
* Flask



## Prerequisites
- **CDR receiver URI**: In the CMS, the recipient device to which to send the CDR messages to needs to be configured. 
   - **Getting the URI**: In this prototype, the CDR receiver is the device on which the Flask app is running. The URI listening to the CDR messages sent from the CMS is therefore the public IP address of the device listening on port 5000 and taking the following format: `http://<public ip address>:5000/cdr`. The public IP address can for example be found with the `ipconfig` command on Windows. 
   - **Adding the URI as CDR receiver to the CMS**:
     1. Open the CMS web admin interface.
     2. Go to **Configure > CDR settings**.
     3. Add the CDR receiver URI as one of the four Receiver URIs.
     4. Repeat steps 1 to 3 for each CMS if clustered. 
     - Alternatively, this can be done using the CMS API. Instructions can be found in the [CDR Guide](https://www.cisco.com/c/dam/en/us/td/docs/conferencing/ciscoMeetingServer/Reference_Guides/Version-2-9/Cisco-Meeting-Server-CDR-Guide-2-9.pdf) under *Configuring the Recipient Devices*. 



## Installation

1. Clone this repository with `git clone <this repo>`.

2. Open the `credentials.yml` file, and fill in the following variables: 
        
        username: ''  # username to CMS
        password: ''# password to CMS
        cms_ips:
            - '' # list of FQDNs of CMS(s)
        port: '' # https port on CMS
        secure_domains:
            - '' # list of secure domains to identify secure participants (security level 1)
        internal_domains:
            - '' # list of internal domains to identify interanl Jabber participants (security level 2) 

3. (Optional) Create a Python virtual environment and activate it (find instructions [here](https://docs.python.org/3/tutorial/venv.html)).

4. Navigate to the root directory of the repository in the terminal, and install the requirements with `pip install -r requirements.txt`.

5. Start the Flask app with `python main.py`.

6. You can now start your calls. NB: The Flask app will only consider calls that are started *atfer* Step 5 of the installation.



## License
Provided under Cisco Sample Code License, for details see [LICENSE](./LICENSE).



## Code of Conduct
Our code of conduct is available [here](./CODE_OF_CONDUCT.md).



## Contributing
See our contributing guidelines [here](./CONTRIBUTING.md).
