"""Mock gateway implementations for testing."""
from typing import Dict, Any, List, Optional
from datetime import datetime


class MockGatewayClient:
    """Mock Gateway client for testing."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize mock gateway client."""
        self.base_url = base_url
        self._requests: List[Dict[str, Any]] = []
        self._responses: Dict[str, Any] = {}
        self._connected = False
    
    def connect(self):
        """Mock gateway connection."""
        self._connected = True
    
    def disconnect(self):
        """Mock gateway disconnection."""
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected
    
    def send_request(self, endpoint: str, method: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock send request."""
        request = {
            "endpoint": endpoint,
            "method": method,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._requests.append(request)
        
        # Return mock response
        response_key = f"{method}:{endpoint}"
        return self._responses.get(response_key, {"status": "success", "data": {}})
    
    def set_mock_response(self, endpoint: str, method: str, response: Dict[str, Any]):
        """Set a mock response for testing."""
        response_key = f"{method}:{endpoint}"
        self._responses[response_key] = response
    
    def get_requests(self) -> List[Dict[str, Any]]:
        """Get all requests made."""
        return self._requests
    
    def reset(self):
        """Reset mock state."""
        self._requests.clear()
        self._responses.clear()
