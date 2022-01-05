#!/usr/bin/env python
# coding: utf-8

### About
# Simulating asset prices using Monte Carlo Simulations.

### Code

import sys
import os
import logging
import numpy as np
import pandas as pd
import boto3
from botocore.exceptions import ClientError

# N.B.: Don't set random seed as we want randomness in our Monte Carlo simulations!
# np.random.seed(42)

## ENVIRONMENT VARIABLES
# No. of days to perform Monte Carlo simulations for
N_PERIODS = os.getenv("N_PERIODS")
# No. of Monte Carlo simulations to run in this job
N_SIMS = os.getenv("N_SIMS")
# bucket name to upload final results to
BUCKET_NAME = os.getenv("AWS_BUCKET")
# Folder for storing all data for this Batch job
JOB_NAME = os.getenv("JOB_NAME")
# get index of AWS Batch array job that this job is assigned
JOB_INDEX = os.getenv("AWS_BATCH_JOB_ARRAY_INDEX")

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

# check all required environment variables are defined
check_env_var(N_PERIODS, "N_PERIODS")
check_env_var(N_SIMS, "N_SIMS")
check_env_var(BUCKET_NAME, "AWS_BUCKET")
check_env_var(JOB_NAME, "JOB_NAME")
check_env_var(JOB_INDEX, "AWS_BATCH_JOB_ARRAY_INDEX")

# convert to appropriate data type
N_PERIODS = int(N_PERIODS)
N_SIMS = int(N_SIMS)

# get asset prices from CSV file in S3 bucket
asset_prices = get_input_csv(BUCKET_NAME, JOB_NAME+"/input/asset_prices.csv")
# compute the quantities in Eq.(1) above from the data
log_returns = np.log(1 + asset_prices.pct_change())
u = log_returns.mean()
var = log_returns.var()
drift = u - (0.5*var)
stdev = log_returns.std()
# generate standard normal variate of required size
if len(u) > 1:
    Z = np.random.multivariate_normal(mean=[0]*len(u), cov=log_returns.cov(), size=(N_PERIODS, N_SIMS))
else:
    Z = np.random.normal(size=(N_PERIODS, N_SIMS))
# endif #
# since mu and sigma are daily values, dt=1
daily_returns = np.exp(drift.values + stdev.values * Z)
price_paths = np.zeros_like(daily_returns)
price_paths[0] = asset_prices.iloc[-1]
# evolve price stochastically as per the model in Eq.(1) above
for t in range(1, N_PERIODS):
    price_paths[t] = price_paths[t-1]*daily_returns[t]
# endfor #
# Get the final asset prices for each Monte Carlo run
x = pd.DataFrame(np.round(price_paths[-1],2), columns=asset_prices.columns)
# upload to S3 bucket output
of_name =  "mc_sim_results" + "_"
of_name += JOB_INDEX + ".csv"
x.to_csv(of_name)
obj_name = JOB_NAME + "/output/" + of_name
if upload_file(of_name, BUCKET_NAME, obj_name):
    print(f"Uploaded final results of Monte Carlo simulations to S3 bucket {BUCKET_NAME} as {obj_name}")
else:
    print(f"Failed to upload results of Monte Carlo simulations to S3 bucket {BUCKET_NAME}")
# endif #

