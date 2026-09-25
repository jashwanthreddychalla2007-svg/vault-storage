import json
import re
from typing import Dict, Any, List

class S3IAMGateway:
    """AWS S3 Compatibility Gateway, IAM Policy Simulator, and SDK Code Snippet Generator."""

    @staticmethod
    def evaluate_iam_policy(policy_json: Dict[str, Any], action: str, resource: str) -> Dict[str, Any]:
        """Evaluates AWS S3 IAM JSON Policy against requested action and bucket/object resource."""
        statements = policy_json.get("Statement", [])
        
        # Default Explicit Deny rule per AWS Security Standard
        decision = "DENY"
        matching_statement = None

        for stmt in statements:
            effect = stmt.get("Effect", "Deny")
            actions = stmt.get("Action", [])
            resources = stmt.get("Resource", [])

            if isinstance(actions, str):
                actions = [actions]
            if isinstance(resources, str):
                resources = [resources]

            # Match action (wildcard support e.g. s3:*)
            action_match = any(
                a == "*" or a == action or (a.endswith("*") and action.startswith(a[:-1]))
                for a in actions
            )

            # Match resource (wildcard support e.g. arn:aws:s3:::mybucket/*)
            resource_match = any(
                r == "*" or r == resource or (r.endswith("*") and resource.startswith(r[:-1]))
                for r in resources
            )

            if action_match and resource_match:
                if effect == "Deny":
                    return {
                        "decision": "DENY",
                        "reason": f"Explicit Deny in statement '{stmt.get('Sid', 'Unnamed')}'",
                        "eval_context": {"action": action, "resource": resource}
                    }
                elif effect == "Allow":
                    decision = "ALLOW"
                    matching_statement = stmt.get("Sid", "Unnamed")

        return {
            "decision": decision,
            "reason": f"Allowed by statement '{matching_statement}'" if decision == "ALLOW" else "Implicit Deny: No matching Allow statement",
            "eval_context": {"action": action, "resource": resource}
        }

    @staticmethod
    def generate_sdk_snippets(bucket: str, object_key: str, endpoint: str = "http://localhost:8000") -> Dict[str, str]:
        """Generates executable AWS S3 SDK code snippets across 5 popular languages."""
        
        curl_snippet = f"""# Curl S3 Compatible GET Object Request
curl -X GET "{endpoint}/api/v1/buckets/{bucket}/objects/{object_key}" \\
  -H "Authorization: Bearer vault_live_8f992a71" \\
  -H "x-user-role: developer" \\
  --output "{object_key}" """

        python_boto3 = f"""# Python boto3 S3 Client Connection
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='{endpoint}',
    aws_access_key_id='vault_access_key_2026',
    aws_secret_access_key='vault_secret_key_2026',
    region_name='us-east-1'
)

# Download Object
s3.download_file('{bucket}', '{object_key}', './{object_key}')
print("Successfully downloaded {object_key} from Vault S3 Engine!")"""

        node_sdk = f"""// Node.js @aws-sdk/client-s3 Example
import {{ S3Client, GetObjectCommand }} from "@aws-sdk/client-s3";
import fs from "fs";

const client = new S3Client({{
  endpoint: "{endpoint}",
  region: "us-east-1",
  credentials: {{ accessKeyId: "vault_access_key_2026", secretAccessKey: "vault_secret_key_2026" }}
}});

const command = new GetObjectCommand({{ Bucket: "{bucket}", Key: "{object_key}" }});
const response = await client.send(command);
response.Body.pipe(fs.createWriteStream("./{object_key}"));"""

        go_sdk = f"""// Go aws-sdk-go-v2 Example
package main

import (
    "context"
    "fmt"
    "github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/s3"
)

func main() {{
    cfg, _ := config.LoadDefaultConfig(context.TODO(), config.WithRegion("us-east-1"))
    client := s3.NewFromConfig(cfg, func(o *s3.Options) {{
        o.BaseEndpoint = aws.String("{endpoint}")
    }})

    output, err := client.GetObject(context.TODO(), &s3.GetObjectInput{{
        Bucket: aws.String("{bucket}"),
        Key:    aws.String("{object_key}"),
    }})
    fmt.Println("Downloaded Vault S3 Object:", output.ContentLength)
}}"""

        aws_cli = f"""# AWS CLI Command targeting local Vault S3 Gateway
aws s3 cp s3://{bucket}/{object_key} ./{object_key} \\
  --endpoint-url {endpoint} \\
  --no-verify-ssl"""

        return {
            "curl": curl_snippet,
            "python_boto3": python_boto3,
            "node_sdk": node_sdk,
            "go_sdk": go_sdk,
            "aws_cli": aws_cli
        }
