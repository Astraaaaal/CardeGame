"""
Client Cloudinary — Upload et génération d'URLs.
"""

import cloudinary
import cloudinary.uploader
from app.config import settings


def configure_cloudinary():
    """Configure le SDK Cloudinary (à appeler au startup)."""
    if settings.CLOUDINARY_CLOUD_NAME:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )


def upload_image(file_path: str, public_id: str, folder: str = "cards") -> str:
    """
    Upload une image vers Cloudinary.
    Retourne l'URL sécurisée.
    """
    result = cloudinary.uploader.upload(
        file_path,
        public_id=public_id,
        folder=f"cardegame/{folder}",
        overwrite=False,
        resource_type="image",
    )
    return result["secure_url"]


def get_card_image_url(public_id: str) -> str:
    """Génère l'URL d'une carte rendue."""
    return cloudinary.CloudinaryImage(
        f"cardegame/cards/{public_id}"
    ).build_url(format="png", quality="auto")


def upload_image_bytes(image_bytes: bytes, public_id: str, folder: str = "cards") -> str:
    """
    Upload des bytes d'image vers Cloudinary.
    Retourne l'URL sécurisée.
    """
    result = cloudinary.uploader.upload(
        image_bytes,
        public_id=public_id,
        folder=f"cardegame/{folder}",
        overwrite=False,
        resource_type="image",
    )
    return result["secure_url"]
