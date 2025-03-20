import ibm_boto3
from ibm_botocore.client import Config
import os
import time
import json

# Load IBM Cloud Object Storage credentials from JSON files

def load_cos_credentials(file_path):
    try:
        with open(file_path, 'r') as file:
            credentials = json.load(file)
        return credentials
    except Exception as e:
        print(f"Error loading credentials from {file_path}: {e}")
        return None

# Load the credentials for Main Server and Backup Server
main_server_cos_credentials = load_cos_credentials("main_server_credentials.json")
backup_server_cos_credentials = load_cos_credentials("backup_server_credentials.json")

if not main_server_cos_credentials or not backup_server_cos_credentials:
    print("Error loading credentials. Exiting.")
    exit(1)

# Create resource client for Main Server
main_server_cos = ibm_boto3.client('s3',
                                   ibm_api_key_id=main_server_cos_credentials['api_key'],
                                   ibm_service_instance_id=main_server_cos_credentials['service_instance_id'],
                                   config=Config(signature_version='oauth'),
                                   endpoint_url=main_server_cos_credentials['endpoint'])

# Create resource client for Backup Server
backup_server_cos = ibm_boto3.client('s3',
                                     ibm_api_key_id=backup_server_cos_credentials['api_key'],
                                     ibm_service_instance_id=backup_server_cos_credentials['service_instance_id'],
                                     config=Config(signature_version='oauth'),
                                     endpoint_url=backup_server_cos_credentials['endpoint'])

# Now, Copy the file from Main Server's bucket to Backup Server's bucket
def backup_files():
    try:
        # List objects in the Main Server bucket
        objects = main_server_cos.list_objects_v2(Bucket=main_server_cos_credentials['bucket_name'])
        if 'Contents' in objects:
            print(f"Found {len(objects['Contents'])} objects in the main server bucket.")

            # List objects in the Backup Server bucket to compare timestamps
            backup_objects = backup_server_cos.list_objects_v2(Bucket=backup_server_cos_credentials['bucket_name'])
            backup_files = {obj['Key']: obj['LastModified'] for obj in backup_objects.get('Contents', [])}

            # Iterate through each object and copy it to the Backup Server bucket if new or modified
            for obj in objects['Contents']:
                file_name = obj['Key']
                main_last_modified = obj['LastModified']
                print(f"Checking: {file_name}")

                # Check if the file exists in the Backup Server and if it is newer or not present
                if file_name not in backup_files or main_last_modified > backup_files[file_name]:
                    print(f"Backing up: {file_name}")

                    try:
                        # Copy object from Main Server bucket to Backup Server bucket
                        copy_source = {'Bucket': main_server_cos_credentials['bucket_name'], 'Key': file_name}
                        backup_server_cos.copy_object(CopySource=copy_source,
                                                      Bucket=backup_server_cos_credentials['bucket_name'],
                                                      Key=file_name)
                        print(f"Successfully backed up: {file_name}")
                    except Exception as e:
                        print(f"Error backing up {file_name}: {str(e)}")
                else:
                    print(f"No need to back up (unchanged): {file_name}")
        else:
            print("No objects found in the main server bucket.")
    except Exception as e:
        print(f"Error listing objects from the main server bucket: {str(e)}")

# Run the backup every 5 minutes (300 seconds)
while True:
    backup_files()  # Perform the backup
    print("Waiting 10 minutes before the next backup...")
    time.sleep(600)  # Wait for 10 minutes before running again