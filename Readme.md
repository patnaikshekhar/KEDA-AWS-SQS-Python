# KEDA SQS Python Example

This is an example of using [KEDA](https://github.com/kedacore/keda) with AWS SQS and python.

KEDA (Kubernetes-based Event Driven Autoscaling) allows you to auto scale your kubernetes pods based on external metrics derived from systems such as RabbitMQ, AWS SQS, Azure Storage Queues, Azure ServiceBus, etc. It also lets your scale the number of pods to zero so that you're not consuming resources when there is no processing to be done.

# Prerequisites
You need a Kubernetes cluster with KEDA installed. The [KEDA git hub repository](https://github.com/kedacore/keda) explains how this can be done using Helm.

You will also need to make sure that you are using the image tag: master
```sh
helm upgrade keda-edge kedacore/keda-edge \
  --devel \
  --set logLevel=debug \
  --set image.tag=master \
  --namespace keda
```

# Tutorial

We'll start of by cloning this repository and creating a queue in SQS

```sh
git clone https://github.com/patnaikshekhar/KEDA-AWS-SQS-Node
cd KEDA-AWS-SQS-Node

# Configure the AWS CLI with your access key and secret
aws configure

# Create a SQS Queue
QUEUE_NAME=keda-test
REGION=us-west-2

QueueURL=$(aws sqs create-queue \
  --queue-name=$QUEUE_NAME \
  --region=$REGION \
  --output=text \
  --query=QueueUrl)
```

Next we'll create a namespace and secret with out AWS Access Key and Secret.

You will need to replace the values with your Access Key and Secret

```sh
AWS_ACCESS_KEY_ID=[REPLACE WITH YOUR AWS ACCESS KEY]
AWS_SECRET_ACCESS_KEY=[REPLACE WITH YOUR AWS ACCESS SECRET]

# Create a new namespace
kubectl create namespace keda-aws-sqs-sample

# Create a kubernetes secret with AWS Access Key and secret
kubectl create secret generic keda-aws-secrets \
  --namespace=keda-aws-sqs-sample \
  --from-literal=AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  --from-literal=AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
```

We shall now  deploy the kubernetes objects. We'll be creating a Deployment and a ScaledObject. The deployment is for a simple python program that removes a message from SQS and then writes it to standard out. The scaled object is a CRD used by KEDA to determine which deployment to scale and using which metrics. In this case we're looking at the queue length as the metric.

This is what the definition for the scaled object looks like

```yaml
apiVersion: keda.k8s.io/v1alpha1
kind: ScaledObject
metadata:
  name: aws-sqs-queue-scaledobject
  namespace: keda-aws-sqs-sample
spec:
  scaleTargetRef:
    deploymentName: keda-aws-sqs-python
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: <QUEUE_URL>
      region: "us-west-2"
      awsAccessKeyID: AWS_ACCESS_KEY_ID
      awsSecretAccessKey: AWS_SECRET_ACCESS_KEY
      queueLength: "5"
```

The scaleTargetRef points to the deployment. The awsAccessKeyID and awsSecretAccessKey variables are set to the name of the environment variables passed to the deployment.

The following is the deployment for the python app:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: keda-aws-sqs-python
  namespace: keda-aws-sqs-sample
spec:
  selector:
    matchLabels:
      service: keda-aws-sqs-python
  replicas: 1
  template:
    metadata:
      labels:
        service: keda-aws-sqs-python
    spec:
      containers:
      - image: patnaikshekhar/keda-aws-sqs-python:1
        name: consumer
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: keda-aws-secrets
              key: AWS_ACCESS_KEY_ID
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: keda-aws-secrets
              key: AWS_SECRET_ACCESS_KEY
        - name: AWS_DEFAULT_REGION
          value: us-west-2
```

```sh
# Replace the name of the queue url in the scaledobject manifest. This can also be done
# manually
sed -i -e "s/<QUEUE_URL>/${QueueURL}/g" ./manifests/scaledobject.yaml

# Deploy the kubernetes objects
kubectl apply -f manifests/
```

We can now open a terminal window to start monitoring the pods. You should see no pods started at this point.

```sh
kubectl get pods -n keda-aws-sqs-sample -w
```

Now that the queue is created we're ready to test by placing messages into the queue. Run the following commands to place 20 messages into the queue

```sh
for x in {1..20}
do
aws sqs send-message \
  --message-body="Test Message ${x}" \
  --queue-url=$QueueURL \
  --region=$REGION
done
```

You should now see pods automatically spinning up to process the message. Once all the messages have been processed you would be able to see the pods getting terminated.
