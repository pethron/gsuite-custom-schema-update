from __future__ import print_function
import pickle
import os.path
import yaml
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']
API_SERVICE = 'admin'
API_VERSION = 'directory_v1'


def get_credentials():
    """Shows basic usage of the Admin SDK Directory API.
    Prints the emails and names of the first 10 users in the domain.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_path = os.path.join(os.getcwd(), 'credentials.json')
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def update_saml_attributes(service, user, schema_config, federations, session_duration=28800):
    custom_schema_roles = []
    for federation in federations:
        custom_schema_roles.append(
            {
                'type': 'work',
                'value': "arn:aws:iam::{0}:role/{1},arn:aws:iam::{0}:saml-provider/{2}".format(
                    federation['account'], federation['role'], federation['provider'])
            }
        )

    current_schemas = user['customSchemas']
    user['customSchemas'][schema_config['name']] = {
        schema_config['session']: session_duration,
        schema_config['role']: custom_schema_roles
    }

    user.update({'customSchemas': current_schemas})
    ret = service.users().update(userKey=user['id'], body=user).execute()

    return ret['customSchemas']


def main():
    # Load the custom schema file
    custom_schema_file = os.path.join(os.getcwd(), 'custom-schema.yaml')
    with open(custom_schema_file, "r") as yaml_file:
        schema_config = yaml.safe_load(yaml_file)

    # Load the federation file
    federation_file = os.path.join(os.getcwd(), 'federation.yaml')
    with open(federation_file, "r") as yaml_file:
        federations = yaml.safe_load(yaml_file)

    # Get credentials and build the service client
    creds = get_credentials()
    service = build(API_SERVICE, API_VERSION, credentials=creds)

    # Call the Admin SDK Directory API
    orgPath = "orgUnitPath='/'" # If need change like "orgUnitPath='/<my organizational unit>'"
    results = service.users().list(customer='my_customer',
                                   projection="full",
                                   query=orgPath,
                                   maxResults=2,
                                   orderBy='email').execute()
    users = results.get('users', [])

    if not users:
        print('No users in the domain.')
    else:
        print('Update users with the following customSchemas')
        for user in users:
            for email in user['emails']:
                for federation in federations:
                    if federation['email'] == email['address']:
                        userUpdated = update_saml_attributes(service, user, schema_config, federation['federations'])
                        print(u'{0} {1} {2}'.format(user['primaryEmail'], user['id'], userUpdated))


if __name__ == '__main__':
    main()