import boto3

# Create SQS client
sqs = boto3.client("sqs", region_name="us-west-2")

queue_url = ""

# Send message to SQS queue

for i in range(50):
    sqs.send_message(QueueUrl=queue_url, MessageBody=(f"hello world {i}"))
