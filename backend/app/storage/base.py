from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class SessionStore(ABC):
    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        pass


class BaseExemplarStore(ABC):
    @abstractmethod
    def add_exemplar(self, exemplar: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_stats(self, exemplar_id: str, success: bool) -> None:
        pass

    @abstractmethod
    def update_status(self, exemplar_id: str, status: str) -> None:
        pass

    @abstractmethod
    def delete(self, exemplar_id: str) -> None:
        pass


class RequestLogStore(ABC):
    @abstractmethod
    def log_request(self, log_entry: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_metrics_summary(self) -> Dict[str, Any]:
        pass
