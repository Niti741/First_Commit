"""
AWS Adapters Stub for future cloud deployment.
Maps business abstractions (SessionStore, ExemplarStore, RequestLogStore) to AWS primitives
(DynamoDB, S3, CloudWatch) without requiring boto3 or AWS credentials during local development.
"""
from typing import Dict, List, Optional, Any
from backend.app.storage.base import SessionStore, BaseExemplarStore, RequestLogStore


class DynamoDBSessionStore(SessionStore):
    """
    Future AWS adapter:
    Table: KifayatSessions (PartitionKey: session_id)
    Attributes: raw_turns, frozen_blocks, merged_blocks, turn_count, updated_at
    """
    def __init__(self, table_name: str = "KifayatSessions", region: str = "us-east-1"):
        self.table_name = table_name
        self.region = region

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("DynamoDB adapter enabled in AWS environment via AWS_REGION and credentials.")

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        raise NotImplementedError("DynamoDB adapter enabled in AWS environment.")

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError("DynamoDB adapter enabled in AWS environment.")


class DynamoDBExemplarStore(BaseExemplarStore):
    """
    Future AWS adapter:
    Table: KifayatExemplars (PartitionKey: id, GSI: category, status)
    """
    def __init__(self, table_name: str = "KifayatExemplars", region: str = "us-east-1"):
        self.table_name = table_name
        self.region = region

    def add_exemplar(self, exemplar: Dict[str, Any]) -> None:
        raise NotImplementedError("DynamoDB adapter enabled in AWS environment.")

    def get_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError("DynamoDB adapter enabled in AWS environment.")

    def update_stats(self, exemplar_id: str, success: bool) -> None:
        raise NotImplementedError("DynamoDB adapter enabled in AWS environment.")

    def update_status(self, exemplar_id: str, status: str) -> None:
        raise NotImplementedError("DynamoDB adapter enabled in AWS environment.")

    def delete(self, exemplar_id: str) -> None:
        raise NotImplementedError("DynamoDB adapter enabled in AWS environment.")


class CloudWatchRequestLogStore(RequestLogStore):
    """
    Future AWS adapter:
    CloudWatch Embedded Metric Format (EMF) and DynamoDB request log archival.
    """
    def __init__(self, log_group: str = "/kifayat/gateway/requests", region: str = "us-east-1"):
        self.log_group = log_group
        self.region = region

    def log_request(self, log_entry: Dict[str, Any]) -> None:
        raise NotImplementedError("CloudWatch EMF logger enabled in AWS environment.")

    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        raise NotImplementedError("CloudWatch logs enabled in AWS environment.")

    def get_metrics_summary(self) -> Dict[str, Any]:
        raise NotImplementedError("CloudWatch metrics enabled in AWS environment.")
