"""Redis-based conversation checkpointer for production"""
import json
import redis
from typing import Any, Dict, Optional, Iterator, Tuple
from datetime import timedelta
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple
from config import Config


class RedisCheckpointer(BaseCheckpointSaver):
    """Redis-based checkpointer with TTL support"""
    
    def __init__(self, redis_client: redis.Redis, ttl: int = 86400):
        """
        Initialize Redis checkpointer
        
        Args:
            redis_client: Redis client instance
            ttl: Time to live for checkpoints in seconds (default: 24 hours)
        """
        self.redis = redis_client
        self.ttl = ttl
    
    def put(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: Dict[str, Any], new_versions: Dict[str, Any] = None) -> Dict[str, Any]:
        """Save checkpoint to Redis"""
        thread_id = config["configurable"]["thread_id"]
        key = f"checkpoint:{thread_id}"
        
        data = {
            "checkpoint": checkpoint,
            "metadata": metadata
        }
        
        self.redis.setex(
            key,
            timedelta(seconds=self.ttl),
            json.dumps(data, default=str)
        )
        
        return config
    
    def get(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Retrieve checkpoint from Redis"""
        thread_id = config["configurable"]["thread_id"]
        key = f"checkpoint:{thread_id}"
        data = self.redis.get(key)
        
        if data:
            loaded = json.loads(data)
            return CheckpointTuple(
                config=config,
                checkpoint=loaded["checkpoint"],
                metadata=loaded.get("metadata", {}),
                parent_config=None
            )
        return None
    
    def list(self, config: Dict[str, Any]) -> Iterator[CheckpointTuple]:
        """List checkpoints (returns empty iterator for Redis)"""
        return iter([])
    
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Get checkpoint tuple"""
        return self.get(config)
    
    def put_writes(self, config: Dict[str, Any], writes: list, task_id: str) -> None:
        """Store pending writes"""
        pass


def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    return redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=Config.REDIS_DB,
        password=Config.REDIS_PASSWORD if Config.REDIS_PASSWORD else None,
        decode_responses=False,
        socket_timeout=5,
        socket_connect_timeout=5,
    )


def get_checkpointer() -> BaseCheckpointSaver:
    """Get checkpointer instance (Redis or fallback to Memory)"""
    try:
        redis_client = get_redis_client()
        redis_client.ping()  # Test connection
        import logging
        logging.info("Redis connection successful, using RedisCheckpointer")
        return RedisCheckpointer(redis_client, ttl=Config.CONVERSATION_TTL)
    except Exception as e:
        import logging
        logging.warning(f"Redis connection failed, falling back to MemorySaver: {e}")
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()

