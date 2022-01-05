import os
import sys
import numpy as np
import pandas as pd
import boto3

## ENVIRONMENT VARIABLES
BUCKET_NAME = os.getenv("AWS_BUCKET")
# Folder for storing all data for this Batch job
JOB_NAME = os.getenv("JOB_NAME")

## Helper functions
def check_env_var(a_var, a_var_name):
    """ Check that an expected environment variable is actually present.

    :param a_var: Variable to be checked
    :param a_var_name: Name of environment variable that should be present
    :return: None; exit program if variable is not present
    """
    if a_var is None:
        print(f"Environment variable {a_var_name} is not present!")
        sys.exit(2)
    # endif #
# enddef check_env_var() #

def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)
    # endif #

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    # endtry #
    return True
# enddef upload_file() #

def get_input_csv(bucket_name, file_name):
    """ Download and read CSV file from an S3 bucket

    :param bucket_name: Bucket in which CSV file is located
    :param file_name: key name of the CSV file to read
    :return: DataFrame constructed from CSV file
    """
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket_name, Key=file_name)
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    if status == 200:
        print(f"Retrieved file {file_name} from bucket {bucket_name}")
        return pd.read_csv(response.get("Body"), index_col=0)
    else:
        print(f"Error in retrieving file {file_name} from bucket {bucket_name}; {status}")
        sys.exit(1)
    # endif #
# enddef get_input_csv() #

def list_csv_files(bucket_name, folder_name=""):
    """ List all CSV files in a given folder in S3 bucket

    :param bucket_name: Bucket in which CSV files is located
    :param folder_name: Folder in bucket in which CSV files reside
    :return: List of names of CSV files in given bucket
    """
    files = []
    s3 = boto3.client('s3')
    for f in s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_name)["Contents"]:
        # only get CSV files
        if f["Key"].split('.')[-1] == 'csv':
            files.append(f["Key"])
        # endif
    # endfor #
    return files
# enddef list_csv_files() #

# check all required environment variables are defined
check_env_var(BUCKET_NAME, "AWS_BUCKET")
check_env_var(JOB_NAME, "JOB_NAME")

# gather results of all Monte Carlo runs
output_folder = JOB_NAME+"/output/"
mc_results_files = list_csv_files(BUCKET_NAME, output_folder)
mc_results = []
for f in mc_results_files:
    mc_results.append(get_input_csv(BUCKET_NAME, f))
# endfor #
# combine final price predictions from all MC simulations in one dataframe
x = pd.concat(mc_results, ignore_index=True)
# compute statistics on the combined results
op = pd.DataFrame(index=x.columns)
op['Mean price [$]'] = np.round(x.mean(axis=0),2)
op['Std Dev [$]'] = np.round(x.std(axis=0),2)
op['5% quantile [$]'] = np.round(np.percentile(x,5,axis=0),2)
op['95% quantile [$]'] = np.round(np.percentile(x,95,axis=0),2)
result_file = 'asset_price_distribution.txt'
op.to_string(result_file, col_space=23)
obj_name = output_folder + result_file
if upload_file(result_file, BUCKET_NAME, obj_name):
    print(f"Uploaded final results of analysis to S3 bucket {BUCKET_NAME} as {obj_name}")
else:
    print(f"Failed to upload results of Monte Carlo simulations to S3 bucket {BUCKET_NAME}")
# endif #

