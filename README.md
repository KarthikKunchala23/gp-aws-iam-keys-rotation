# AWS IAM Access Key Rotation Automation

A modular, configuration-driven Python automation tool for managing AWS IAM access-key rotation with controlled application handoff, observation, deactivation, and deletion.

The solution automates the complete lifecycle of long-lived IAM access keys while providing a controlled handoff mechanism for applications and developers.

---

## Overview

Long-lived AWS IAM access keys can become a security risk when they are not rotated regularly.

This project automates access-key rotation based on a configurable key-age threshold.

Instead of immediately disabling an existing key after creating a replacement, the solution introduces a controlled handoff workflow:

```text
Old Key Exceeds Threshold
        │
        ▼
Create Replacement Key
        │
        ▼
Store New Credentials in Secrets Manager
        │
        ▼
Send SNS Notification
        │
        ▼
Developer/Application Handoff
        │
        ▼
HTTPS Confirmation
        │
        ▼
Observation Period
        │
        ▼
Deactivate Old Key
        │
        ▼
Retention Period
        │
        ▼
Delete Old Key
```

The design is intentionally modular and function-based rather than object-oriented.

---

# Architecture

```text
                         ┌─────────────────────────────┐
                         │     EventBridge Scheduler    │
                         │                             │
                         │ Daily - 18:00 Asia/Kolkata │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   rotation_iam_keys Lambda  │
                         │                             │
                         │ rotation_runner.py          │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │     rotation_engine.py      │
                         │                             │
                         │ collect_rotation_results()  │
                         │ rotate_old_keys()           │
                         │ process_deactivated_keys()  │
                         │ run_rotation()              │
                         └──────────────┬──────────────┘
                                        │
                ┌───────────────────────┼───────────────────────┐
                │                       │                       │
                ▼                       ▼                       ▼
          ┌───────────┐          ┌────────────┐         ┌───────────────┐
          │    IAM    │          │ DynamoDB   │         │ Secrets       │
          │           │          │            │         │ Manager       │
          │ Access    │          │ Rotation   │         │               │
          │ Keys      │          │ State      │         │ Credentials   │
          └───────────┘          └────────────┘         └───────┬───────┘
                                                                 │
                                                                 ▼
                                                          ┌────────────┐
                                                          │    SNS     │
                                                          │            │
                                                          │ Handoff    │
                                                          │ Notification│
                                                          └─────┬──────┘
                                                                │
                                                                ▼
                                                        Developer / Team
                                                                │
                                                                │ HTTPS POST
                                                                ▼
                                                        ┌──────────────┐
                                                        │ API Gateway  │
                                                        └──────┬───────┘
                                                               │
                                                               ▼
                                                        Confirmation
                                                          Lambda
                                                               │
                                                               ▼
                                                          DynamoDB
```

---

# Project Structure

```text
gp-aws-iam-keys-rotation/
│
├── README.md
│
├── config/
│   └── config.yaml
│
├── lambda/
│   ├── lambda_function.py
│   └── rotation_runner.py
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── iam.py
│   ├── iam_key_rotation.py
│   ├── logger.py
│   ├── main.py
│   ├── notifications.py
│   ├── rotation_engine.py
│   ├── rotation_state.py
│   ├── secretsManager.py
│   └── validation.py
│
└── requirements.txt
```

---

# Module Responsibilities

## `src/config.py`

Responsible for loading and retrieving configuration.

Functions include:

```python
load_config()
get_team_config()
get_rotation_config()
```

Configuration is maintained in YAML rather than hard-coded into the application.

---

## `src/iam.py`

Provides the IAM API abstraction.

Responsibilities:

* List IAM users
* List access keys
* Deactivate access keys
* Delete access keys

Example operations:

```python
get_iam_users()
get_access_keys()
deactivate_access_key()
delete_access_key()
```

---

## `src/validation.py`

Responsible for access-key validation.

It determines:

* Current key status
* Key age
* Whether rotation is required

The configured threshold determines whether the key is considered valid or requires rotation.

---

## `src/iam_key_rotation.py`

Contains the lower-level IAM rotation operations.

Responsibilities include:

* Creating replacement access keys
* Storing credentials
* Sending notifications
* Deactivating old keys after observation
* Deleting old keys after retention

---

## `src/rotation_state.py`

Maintains rotation lifecycle state in DynamoDB.

The state allows the automation to be safely executed repeatedly without restarting or duplicating a rotation.

Current lifecycle states include:

```text
HANDOFF_PENDING
HANDOFF_CONFIRMED
OLD_KEY_DEACTIVATED
OLD_KEY_DELETED
```

---

## `src/rotation_engine.py`

This is the main reusable orchestration layer.

The engine contains:

```text
collect_rotation_results()
        │
        ▼
rotate_old_keys()
        │
        ▼
process_deactivated_keys()
```

The public orchestration function is:

```python
run_rotation(config)
```

Both the local CLI and AWS Lambda use the same rotation engine.

This avoids duplicating business logic between local execution and AWS execution.

---

## `src/main.py`

The local CLI entrypoint.

Its responsibility is intentionally limited to:

1. Loading configuration
2. Calling the rotation engine
3. Displaying results

The actual rotation logic does not belong in the CLI.

Run locally with:

```bash
PYTHONPATH=src python src/main.py config/config.yaml
```

---

## `lambda/rotation_runner.py`

AWS Lambda entrypoint for scheduled execution.

The Lambda handler is:

```text
rotation_runner.lambda_handler
```

Its responsibilities are:

1. Load configuration
2. Invoke `run_rotation()`
3. Return execution results

The Lambda does not contain the actual rotation business logic.

---

## `lambda/lambda_function.py`

Confirmation Lambda used by API Gateway.

It receives:

```text
POST /rotations/{rotation_id}/confirm
```

The function:

1. Reads the `rotation_id`
2. Retrieves the DynamoDB rotation record
3. Verifies the current state is `HANDOFF_PENDING`
4. Changes the state to `HANDOFF_CONFIRMED`
5. Records the confirmation timestamp

---

# Configuration

Configuration is stored in:

```text
config/config.yaml
```

Example:

```yaml
teams:
  - name: karthik
    iam_user: karthik
    email: karthikkunchala170@gmail.com

  - name: python
    iam_user: python_script_runner
    email: karthikkunchala170@gmail.com

  - name: platform
    iam_user: terraform-execution
    email: karthikkunchala170@gmail.com

rotation:
  threshold_days: 15
  observation_days: 2
  deletion_retention_days: 7

notification:
  sns_topic_arn: arn:aws:sns:ap-south-1:897722700244:iam-key-rotation

confirmation:
  api_base_url: https://nxrraikebk.execute-api.ap-south-1.amazonaws.com
```

## Rotation Configuration

### `threshold_days`

Maximum allowed access-key age before rotation is required.

Current value:

```yaml
threshold_days: 15
```

### `observation_days`

Number of days to observe the new key after handoff confirmation before deactivating the old key.

Current value:

```yaml
observation_days: 2
```

### `deletion_retention_days`

Number of days the old inactive key is retained before permanent deletion.

Current value:

```yaml
deletion_retention_days: 7
```

---

# Rotation Lifecycle

The automation uses a state-driven workflow.

## 1. Key Within Rotation Period

If:

```text
key age <= threshold_days
```

the key remains unchanged.

Example:

```text
Access key age: 0 days
Threshold: 15 days

Result:
KEY IS VALID
```

---

## 2. Rotation Required

If:

```text
key age > threshold_days
```

the system creates a replacement access key.

```text
Old Key
   │
   │ older than 15 days
   ▼
Create New Key
```

The new credentials are stored in Secrets Manager.

---

## 3. Handoff Pending

After the replacement key is created, the team receives an SNS notification.

DynamoDB records:

```text
HANDOFF_PENDING
```

The old key remains active.

The application/developer is expected to update its credentials.

---

## 4. Handoff Confirmation

The team confirms that the application has switched to the new key through:

```text
POST /rotations/{rotation_id}/confirm
```

The confirmation Lambda changes:

```text
HANDOFF_PENDING
        ↓
HANDOFF_CONFIRMED
```

and records:

```text
confirmation_received_at
```

---

## 5. Observation Period

After confirmation, the system waits for the configured observation period.

Current configuration:

```text
2 days
```

During this period:

```text
Old Key: Active
New Key: Active
```

This provides a safety window to detect problems with the new credentials.

---

## 6. Old Key Deactivation

After the observation period expires:

```text
HANDOFF_CONFIRMED
        ↓
OLD_KEY_DEACTIVATED
```

The old key is changed to:

```text
Inactive
```

The new key remains active.

---

## 7. Deletion Retention

The old inactive key is retained for:

```text
7 days
```

This provides a rollback window.

---

## 8. Permanent Deletion

After the retention period:

```text
OLD_KEY_DEACTIVATED
        ↓
OLD_KEY_DELETED
```

The old access key is permanently deleted.

---

# DynamoDB State

The DynamoDB table is:

```text
iam-key-rotation-state
```

Primary key:

```text
rotation_id
```

The rotation ID is generated from:

```text
user_name
old_access_key_id
new_access_key_id
```

Example format:

```text
terraform-execution#OLD_KEY_ID#NEW_KEY_ID
```

A rotation record contains information such as:

```text
rotation_id
user_name
team_name
email
old_access_key_id
new_access_key_id
secret_arn
status
notification_sent_at
notification_message_id
confirmation_received_at
old_key_deactivated_at
old_key_deleted_at
```

This state allows repeated Lambda executions to resume the lifecycle rather than creating duplicate rotations.

---

# AWS Services

## AWS IAM

Used for:

* User discovery
* Access-key discovery
* Access-key creation
* Access-key deactivation
* Access-key deletion

---

## AWS Secrets Manager

Used to securely store the newly generated access-key credentials.

The application should retrieve the new credentials from Secrets Manager rather than receiving the secret directly through the rotation engine output.

---

## Amazon SNS

Used for team notification.

The notification communicates:

* IAM user
* Old access-key ID
* New access-key ID
* Team information
* Confirmation endpoint

---

## Amazon DynamoDB

Used as the persistent state store for the rotation lifecycle.

This prevents the automation from losing its current state between Lambda executions.

---

## Amazon API Gateway

Provides the HTTPS confirmation endpoint:

```text
POST /rotations/{rotation_id}/confirm
```

API Gateway invokes the confirmation Lambda.

---

## AWS Lambda

Two execution paths are used:

### Scheduled rotation

```text
rotation_runner.lambda_handler
```

### Handoff confirmation

```text
lambda_function.lambda_handler
```

---

## EventBridge Scheduler

The rotation Lambda is scheduled using EventBridge Scheduler.

Current schedule:

```text
18:00
Asia/Kolkata
Every day
```

Schedule expression:

```text
cron(0 18 * * ? *)
```

---

# IAM Permissions

## Rotation Lambda Role

The rotation Lambda uses:

```text
rotation_iam_keys-role-64m8r6sz
```

The role has the basic Lambda execution policy plus an inline policy:

```text
IAMKeyRotationPolicy
```

Permissions include:

### IAM

```text
iam:ListUsers
iam:ListAccessKeys
iam:CreateAccessKey
iam:UpdateAccessKey
iam:DeleteAccessKey
```

### DynamoDB

```text
dynamodb:GetItem
dynamodb:PutItem
dynamodb:UpdateItem
```

### Secrets Manager

```text
secretsmanager:CreateSecret
secretsmanager:PutSecretValue
```

### SNS

```text
sns:Publish
```

---

# Scheduler IAM Role

EventBridge Scheduler uses:

```text
iam-key-rotation-scheduler-role
```

The role has permission to invoke:

```text
lambda:InvokeFunction
```

against:

```text
rotation_iam_keys
```

The Lambda resource policy also restricts invocation to the specific Scheduler schedule.

---

# Local Development

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application locally:

```bash
PYTHONPATH=src python src/main.py config/config.yaml
```

---

# Validation

Compile the modules before deployment:

```bash
python -m py_compile src/rotation_engine.py
python -m py_compile src/main.py
python -m py_compile lambda/rotation_runner.py
```

Test the engine import:

```bash
PYTHONPATH=src python -c \
"import rotation_engine; print('rotation_engine import OK')"
```

Test the Lambda runner import locally:

```bash
PYTHONPATH=src:lambda python -c \
"import rotation_runner; print('rotation_runner import OK')"
```

---

# Lambda Deployment

The scheduled Lambda uses:

```text
rotation_runner.lambda_handler
```

The deployment package contains:

```text
rotation_runner.py
config.yaml
config.py
iam.py
iam_key_rotation.py
notifications.py
rotation_engine.py
rotation_state.py
secretsManager.py
validation.py
```

PyYAML must be packaged for the Lambda runtime and architecture.

For the current environment:

```text
Runtime: Python 3.14
Architecture: x86_64
```

The PyYAML binary must therefore be Linux-compatible.

Example:

```bash
pip install PyYAML \
  --target build/ \
  --platform manylinux2014_x86_64 \
  --only-binary=:all:
```

Create the deployment package:

```bash
cd build
zip -r ../rotation-runner.zip .
cd ..
```

Update Lambda:

```bash
aws lambda update-function-code \
  --function-name rotation_iam_keys \
  --zip-file fileb://rotation-runner.zip \
  --region ap-south-1
```

Configure the handler:

```bash
aws lambda update-function-configuration \
  --function-name rotation_iam_keys \
  --handler rotation_runner.lambda_handler \
  --region ap-south-1
```

Verify:

```bash
aws lambda get-function-configuration \
  --function-name rotation_iam_keys \
  --region ap-south-1 \
  --query '[Handler,Runtime,State,LastUpdateStatus]' \
  --output table
```

---

# Manual Lambda Test

The scheduled Lambda can be manually invoked:

```bash
aws lambda invoke \
  --function-name rotation_iam_keys \
  --region ap-south-1 \
  --payload '{}' \
  response.json
```

View the result:

```bash
cat response.json
```

A successful invocation returns:

```json
{
  "statusCode": 200,
  "body": {
    "message": "IAM access-key rotation completed",
    "results": []
  }
}
```

The actual results depend on the current IAM state.

---

# CloudWatch Logs

The Lambda logs are available through:

```text
/aws/lambda/rotation_iam_keys
```

View recent logs:

```bash
aws logs tail /aws/lambda/rotation_iam_keys \
  --since 10m \
  --region ap-south-1
```

Typical output includes:

```text
Starting IAM access-key rotation

Checking for keys that require rotation...

Access key is within rotation period.

Rotation state : HANDOFF_CONFIRMED
Handoff confirmed.
Checking 2-day observation period...

Observation period has not elapsed.

IAM access-key rotation completed
```

---

# API Gateway Confirmation

The confirmation API is:

```text
POST /rotations/{rotation_id}/confirm
```

The base URL is configured in:

```yaml
confirmation:
  api_base_url: ...
```

The confirmation Lambda expects the rotation ID as an API Gateway path parameter.

Example:

```bash
curl -i -X POST \
  "https://<api-id>.execute-api.ap-south-1.amazonaws.com/rotations/<rotation-id>/confirm"
```

Successful confirmation:

```text
HTTP 200
```

Response:

```text
Access key rotation confirmed successfully.
The observation period has started.
```

---

# Operational Safety

The automation intentionally avoids immediately disabling or deleting keys.

The safety model is:

```text
Create replacement
        ↓
Developer/application handoff
        ↓
Explicit confirmation
        ↓
Observation period
        ↓
Deactivate old key
        ↓
Retention period
        ↓
Delete old key
```

This protects applications from immediate credential invalidation.

Repeated scheduler executions are also safe because the DynamoDB state determines what action is currently allowed.

For example:

```text
HANDOFF_PENDING
```

does not create another replacement key.

Similarly:

```text
HANDOFF_CONFIRMED
```

does not immediately deactivate the old key until the observation period has elapsed.

---

# Current Test State

The implementation has been tested against real AWS IAM state.

Example lifecycle:

```text
terraform-execution

Old Key
    │
    ├── Age: 168 days
    └── Active

New Key
    │
    ├── Age: 0 days
    └── Active

DynamoDB:
HANDOFF_CONFIRMED

Result:
Waiting for 2-day observation period
```

Another rotation:

```text
python_script_runner

Old Key
    │
    ├── Age: 275 days
    └── Inactive

New Key
    │
    ├── Age: 0 days
    └── Active

DynamoDB:
OLD_KEY_DEACTIVATED

Result:
Waiting for 7-day deletion retention
```

These states demonstrate that the automation correctly resumes existing rotations rather than creating duplicate credentials.

---

# Scheduled Automation

The production execution path is:

```text
18:00 Asia/Kolkata
        │
        ▼
EventBridge Scheduler
        │
        ▼
rotation_iam_keys Lambda
        │
        ▼
rotation_runner.lambda_handler
        │
        ▼
run_rotation()
        │
        ├── collect_rotation_results()
        ├── rotate_old_keys()
        └── process_deactivated_keys()
```

The system therefore runs unattended once the scheduler is enabled.

---

# Design Principles

## Modular

AWS service interactions are separated from business logic.

## Configuration Driven

Rotation thresholds, observation periods, teams, notifications, and API configuration are externally configurable.

## State Driven

DynamoDB tracks where each rotation currently sits in its lifecycle.

## Safe

Old credentials are not immediately disabled or deleted.

## Idempotent

Repeated scheduler executions evaluate the current state and continue the lifecycle instead of blindly creating new keys.

## Reusable

The same `rotation_engine.py` is used by:

* Local CLI
* Scheduled Lambda

## Minimal Lambda Entry Point

The Lambda handler is responsible only for invocation and configuration loading.

The business logic remains in the reusable engine.

---

# Future Improvements

The current implementation is functional and end-to-end, but the following improvements can further harden it for production.

### 1. Conditional DynamoDB State Transitions

Use DynamoDB conditional updates to prevent race conditions during state changes.

For example:

```text
HANDOFF_CONFIRMED
        ↓
OLD_KEY_DEACTIVATED
```

should only succeed when the stored state is still `HANDOFF_CONFIRMED`.

---

### 2. Failure Recovery

Add explicit handling for failures occurring between:

```text
Create IAM Key
       ↓
Store Secret
       ↓
Send Notification
       ↓
Write DynamoDB State
```

This is especially important because partial success can leave resources in an intermediate state.

---

### 3. Secrets Manager Resource Scoping

The current Lambda policy can be further restricted once the exact secret naming strategy is finalized.

---

### 4. Structured Logging

Replace plain `print()` statements with structured logging containing fields such as:

```text
rotation_id
iam_user
old_access_key_id
new_access_key_id
rotation_state
action
timestamp
```

---

### 5. CloudWatch Alarms

Add alarms for:

* Lambda invocation failures
* Lambda errors
* Scheduler failures
* Unexpected rotation states

---

### 6. Automated Testing

Add unit tests covering:

```text
Key valid
Key requires rotation
Handoff pending
Handoff confirmed
Observation period elapsed
Observation period not elapsed
Old key deactivated
Retention period elapsed
Old key deleted
Unexpected number of keys
```

---

### 7. Infrastructure as Code

The AWS resources can eventually be managed through Terraform:

```text
IAM
DynamoDB
Secrets Manager
SNS
Lambda
API Gateway
EventBridge Scheduler
IAM Roles
IAM Policies
CloudWatch
```

This would make the entire platform reproducible.

---

# Final Architecture

The completed system can be summarized as:

```text
                         DAILY SCHEDULE
                              │
                              ▼
                     EventBridge Scheduler
                              │
                              ▼
                       Rotation Lambda
                              │
                              ▼
                       Rotation Engine
                              │
              ┌───────────────┼────────────────┐
              │               │                │
              ▼               ▼                ▼
             IAM          DynamoDB       Secrets Manager
              │               │                │
              │               │                ▼
              │               │               SNS
              │               │                │
              │               │                ▼
              │               │             Developer
              │               │                │
              │               │                │ HTTPS
              │               │                ▼
              │               │          API Gateway
              │               │                │
              │               │                ▼
              │               │      Confirmation Lambda
              │               │                │
              └───────────────┴────────────────┘
                              │
                              ▼
                    Rotation State Machine
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      HANDOFF_PENDING  HANDOFF_CONFIRMED  OLD_KEY_DEACTIVATED
                                              │
                                              ▼
                                      OLD_KEY_DELETED
```

The result is a controlled, automated IAM access-key lifecycle that combines **AWS IAM, Lambda, EventBridge Scheduler, DynamoDB, Secrets Manager, SNS, and API Gateway** while keeping the Python implementation modular and reusable.
