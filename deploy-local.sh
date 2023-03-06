#!/bin/bash
set -e

while [ $# -gt 0 ]; do
  case "$1" in
  --skip-build)
    SKIP_BUILD="true"
    ;;
  --skip-build=*)
    SKIP_BUILD="${1#*=}"
    ;;
  --profile-name=*)
    PROFILE="${1#*=}"
    ;;
  --environment=*)
    environment="${1#*=}"
    ;;
  --region=*)
    REGION="${1#*=}"
    ;;
  --project_name=*)
    PROJECT_NAME="${1#*=}"
    ;;
  --cfn-path=*)
    CFN_FOLDER_PREFIX="${1#*=}"
    ;;
  --s3-deploy-bucket=*)
    S3_DEPLOY_BUCKET="${1#*=}"
    ;;
  *)
    printf "***************************\n"
    printf "* Error: Invalid argument.*\n"
    printf "Arguments\n"
    printf " --skip-build                                 or --skip-build=1, if exists, skips the build - assumes already have latest code zipped\n"
    printf " --environment='sand'                         set the environment to deploy to\n"
    printf " --region='us-east-1'                         set the region to deploy to\n"
    printf " --project_name='test-project'                set the project name to create the cfn from, defaults to folder deploy-local.sh is run from\n"
    printf " --cfn-path='./cfn'                           sets the relative path to the cfn/tags/parameters, but will leverage a region folder if exists for params\n"
    printf " --s3-deploy-bucket='lambde-cfn-delpoy-bucket'  sets the s3 deploy bucket used to store templates for cfn creation/updates\n"
    printf "***************************\n"
    exit 1
    ;;
  esac
  shift
done
# Set defaults
REGION=${REGION:="us-east-1"}
environment=${environment:="sand"}
PROFILE=${PROFILE:="default"}
PROJECT_NAME=${PROJECT_NAME:=${PWD/*\//}}

if [  -z "${PROJECT_NAME}" ]; then echo "ERROR: Not able to find any project name in script"; exit 1; fi
CFN_FOLDER_PREFIX=${CFN_FOLDER_PREFIX:="./cfn"}
printf "Setting default cfn path to %s\n" "${CFN_FOLDER_PREFIX}"

if [ -z "${S3_DEPLOY_BUCKET}" ]; then
  printf "Must set the s3 deployment bucket for parameters/tags/cfn"
  exit 1
fi
CFN_PARAMETERS_FOLDER_PREFIX=${CFN_FOLDER_PREFIX}
# check the regional folder exists and *.json paramater files are under it
if [ -d "${CFN_FOLDER_PREFIX}/${REGION}/" ] && [ "$(find ${CFN_FOLDER_PREFIX}/${REGION}/*.json | wc -l)" -gt 0 ]; then
  # "Multi-region Deployment"
  CFN_PARAMETERS_FOLDER_PREFIX="${CFN_FOLDER_PREFIX}/$REGION"
  printf "Parameters folder: %s\n" "${CFN_PARAMETERS_FOLDER_PREFIX}"
fi

echo "Project Name: ${PROJECT_NAME}"
echo "Region: ${REGION}"
echo "Env: ${environment}"
echo "BUCKET: ${S3_DEPLOY_BUCKET}"

print_time() {
  JOB_START_TIME=$(date)
  echo ""
  echo "Time: ${JOB_START_TIME}"
  echo ""
}

# Build the artifacts and zip them up
if [ -z "${SKIP_BUILD}" ]; then
  echo "------------------------------------------------------------------------------"
  echo "Building zip file"
  echo "------------------------------------------------------------------------------"
  rm -rf package/
  mkdir -p package/
  pip3 install -r requirements.txt --no-deps -t package 
  rm -rf package/*.dist-info package/__pycache__ package/*-info
  echo 'Cleaning out the pandas and numpy packages in case they are a dependency'
  rm -rf package/pandas package/numpy

  # copy all the user code files to the packages folder
  cd src/
  additional_project_assets=""
  for ((i = 1; i <= $#; i++ )); do
    additional_project_assets="$additional_project_assets ${!i}"
  done
  cd ../

  cp -r src/* $additional_project_assets package/

  cd package
  # Removing nonessential files
  rm -rf *.dist-info __pycache__ *.egg-info
  find . -name '*.so' -type f -exec strip "{}" \;
  # find . -wholename "*/tests/*" -type f -delete
  # find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete

  zip -r9q ${PROJECT_NAME}.zip *
  cp ${PROJECT_NAME}.zip ../${CFN_FOLDER_PREFIX}
  rm ${PROJECT_NAME}.zip
  cd ..
else
    echo "Skipping build..."
fi

echo "------------------------------------------------------------------------------"
echo "Transforming SAM template"
echo "------------------------------------------------------------------------------"
aws cloudformation package --template-file "${CFN_FOLDER_PREFIX}/${PROJECT_NAME}-cfn.yaml" \
  --s3-bucket "${S3_DEPLOY_BUCKET}" \
  --s3-prefix "${PROJECT_NAME}" \
  --output-template-file "${CFN_FOLDER_PREFIX}/${PROJECT_NAME}-cfn-transform.yaml" \
  --profile "${PROFILE}"


echo "------------------------------------------------------------------------------"
echo "Building up the parameters and tags"
echo "------------------------------------------------------------------------------"
# Build up the parameters and Tags
params=$(jq '.[] | 
  .ParameterKey + "=" + 
  if .ParameterValue|type=="array" then 
    .ParameterValue | join(",") 
  else 
    .ParameterValue 
  end' "${CFN_PARAMETERS_FOLDER_PREFIX}/${PROJECT_NAME}-parameters-${environment}.json" |
  sed -e 's/"//g' |
  sed -e $'s/\r//g' | tr '\n' ' ')

# Build tags based on environment-specific tag JSON file
tags=$(cat ${CFN_FOLDER_PREFIX}/${PROJECT_NAME}-tags-common.json |
  jq '.[] | (.Key + "=" +.Value)' |
  sed -n -e 'H;${x;s/\n/ /g;s/^ //;p;}' |
  tr '\n' ' ')
tags=$tags$(cat ${CFN_FOLDER_PREFIX}/${PROJECT_NAME}-tags-${environment}.json |
  jq '.[] | (.Key + "=" +.Value)' |
  sed -n -e 'H;${x;s/\n/ /g;s/^ //;p;}')

echo "params:"
echo $params
echo "tags:"
echo $tags
echo "------------------------------------------------------------------------------"
echo "Updating stack: ${PROJECT_NAME}-${environment} --- $(date)"
echo "------------------------------------------------------------------------------"
deploy=(aws cloudformation deploy 
  --region ${REGION}
  --no-fail-on-empty-changeset
  --template-file "${CFN_FOLDER_PREFIX}/${PROJECT_NAME}-cfn-transform.yaml"
  --stack-name "${PROJECT_NAME}-${environment}"
  --capabilities CAPABILITY_NAMED_IAM
  --parameter-overrides $params
  --profile "${PROFILE}"
  --tags $tags)
eval $(echo ${deploy[@]})

print_time