import runpod
import boto3
import os
import json
import base64
import uuid

# Secrets
aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
region = os.environ.get('AWS_REGION', 'ap-south-1')

# Clients
s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region
)

lambda_client = boto3.client(
    'lambda',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region
)

def upload_base64_video_to_s3(base64_data, data):
    print("Processing upload with data:", data)
    # Check for required keys safely
    generation_id = data.get("generationId")
    email = data.get("email")
    bucket_name = data.get("bucketName", os.environ.get('BUCKET_NAME'))

    if generation_id and email and bucket_name:
        workflow_id = data.get("workflowId", "workflow")
        sub_template_id = data.get("subTemplateId", "sub_template")

        file_key = f"outputs/{workflow_id}/{sub_template_id}/{generation_id}.mp4"

        # Handle data URI prefix
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]

        video_bytes = base64.b64decode(base64_data)

        # 1. Upload to S3
        s3_client.put_object(Bucket=bucket_name,Key=file_key,Body=video_bytes,ContentType='video/mp4')
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_key}"

        # 2. Call Lambda
        trigger_func = data.get("triggerFunc")
        if trigger_func:
            try:
                # Include the URL in the payload sent to your backend
                lambda_payload = {"url": s3_url, **data}
                lambda_client.invoke(
                    FunctionName=trigger_func,
                    InvocationType='Event',
                    Payload=json.dumps(lambda_payload)
                )
                print(f"worker-comfyui - Notified Lambda: {trigger_func}")
            except Exception as e:
                print(f"worker-comfyui - Failed to trigger Lambda: {e}")

        return s3_url
    else:
        # Default fallback branch
        media_id = str(uuid.uuid4())
        user_email = email if email else "anonymous"
        file_key = f"videos/{user_email}/{media_id}.mp4"

        if "," in base64_data:
            base64_data = base64_data.split(",")[1]

        video_bytes = base64.b64decode(base64_data)
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=video_bytes, ContentType='video/mp4')

        return f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_key}"

def validate_input(job_input):
    if job_input is None:
        return None, "Please provide input"

    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON format in input"

    workflow = job_input.get("workflow")
    if workflow is None:
        return None, "Missing 'workflow' parameter"

    return {
        "workflow": workflow,
        "images": job_input.get("images"),
        "client_data": job_input.get("data")
    }, None

def handler(job):
    job_input = job.get("input", {})
    job_id = job.get("id", "no-id-found")

    print(f"MOCK_LOG: Received job {job_id}")

    validated_data, error_message = validate_input(job_input)
    if error_message:
        return {"error": error_message}

    # Extract the custom data object
    client_data = validated_data.get("client_data", {})
    output_media_base64 = video_base64

    try:
        s3_url = upload_base64_video_to_s3(output_media_base64, client_data)
        return {
            "status": "success",
            "s3_url": s3_url,
            "job_id": job_id
        }
    except Exception as e:
        failureFunc = client_data.get("failureFunc", None)
        if failureFunc:
            try:
                lambda_payload = { "reason": f"runpod_job_failed: {str(e)}, job_id:{job_id}",generationId: client_data.get("generationId"), email: client_data.get("email"), credits: client_data.get("credits"), fcmToken: client_data.get("fcmToken"), platform: client_data.get("platform") }
                lambda_client.invoke(
                    FunctionName=failureFunc,
                    InvocationType='Event',
                    Payload=json.dumps(lambda_payload)
                )
                print(f"Notified User with: {failureFunc}")
            catch(Exception as e):
                print("Triggering failure function failed:",e)
        
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
