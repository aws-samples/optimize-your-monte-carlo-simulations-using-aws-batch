#!/bin/bash

### GLOBAL VARIABLES
SIM_IMG="pba-monte-carlo-sim-aws-batch-blog"
COLL_IMG="pba-monte-carlo-coll-aws-batch-blog"
DOCKERFILE="Dockerfile"
TAG="latest"

# Get AWS a/c info
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

if [ $? -ne 0 ]
then
    echo "The call to `aws sts` to get AWS a/c info failed!"
    exit 255
fi

# Get the region defined in the current configuration
REGION=$(aws configure get region)
REGION=${REGION:-us-east-1}
echo "Region: ${REGION}"

SIM_FULLNAME="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${SIM_IMG}:${TAG}"
COLL_FULLNAME="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${COLL_IMG}:${TAG}"

# Get the login command from ECR and execute it directly
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${SIM_FULLNAME}

# Build the sim docker image locally with the image name and then push it to ECR
# with the full name.

cd sim/
echo "Executing 'docker build -t ${SIM_IMG} -f ${DOCKERFILE} .'"
docker build -t ${SIM_IMG} -f ${DOCKERFILE} .

echo "Executing 'docker tag ${SIM_IMG} ${sim_fullname}'"
docker tag ${SIM_IMG} ${SIM_FULLNAME}

echo "Executing 'docker push ${SIM_FULLNAME}'"
docker push ${SIM_FULLNAME}


# Build the coll docker image locally with the image name and then push it to ECR
# with the full name.

cd ../coll/
echo "Executing 'docker build -t ${COLL_IMG} -f ${DOCKERFILE} .'"
docker build -t ${COLL_IMG} -f ${DOCKERFILE} .

echo "Executing 'docker tag ${COLL_IMG} ${coll_fullname}'"
docker tag ${COLL_IMG} ${COLL_FULLNAME}

echo "Executing 'docker push ${coll_fullname}'"
docker push ${COLL_FULLNAME}

# back to original directory
cd ..
