# Authentication and business logic services
from app.services import attention_service
from app.services import interaction_service

# Aliases for backward compatibility
module4_service = attention_service
module5_service = interaction_service

__all__ = [
    "attention_service",
    "interaction_service",
    "module4_service",
    "module5_service",
]
