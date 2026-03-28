"""
NEXUS — Módulo E: Distribución multicanal
Conectores para LinkedIn, Instagram/Facebook, X, YouTube.
Estado: estructura completa, credenciales pendientes de configurar.
"""
import os
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class Platform(str, Enum):
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    X = "x"
    YOUTUBE = "youtube"


@dataclass
class PublishResult:
    platform: Platform
    success: bool
    post_id: str | None = None
    url: str | None = None
    error: str | None = None


class BasePublisher(ABC):
    """Interfaz común para todos los conectores."""

    @abstractmethod
    def is_configured(self) -> bool:
        """True si las credenciales están en el entorno."""
        ...

    @abstractmethod
    async def publish(self, content: str, media_url: str | None = None) -> PublishResult:
        """Publica contenido en la plataforma."""
        ...


# ── LINKEDIN ──────────────────────────────────────────────
class LinkedInPublisher(BasePublisher):
    """
    Conectar: developer.linkedin.com → Create App
    Permisos necesarios: w_member_social, r_liteprofile
    Variables de entorno: LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_ID
    """

    def is_configured(self) -> bool:
        return bool(os.getenv("LINKEDIN_ACCESS_TOKEN") and os.getenv("LINKEDIN_PERSON_ID"))

    async def publish(self, content: str, media_url: str | None = None) -> PublishResult:
        if not self.is_configured():
            return PublishResult(Platform.LINKEDIN, False, error="Credenciales no configuradas")

        token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        person_id = os.getenv("LINKEDIN_PERSON_ID")

        payload = {
            "author": f"urn:li:person:{person_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )

        if resp.status_code == 201:
            post_id = resp.headers.get("x-restli-id", "")
            return PublishResult(Platform.LINKEDIN, True, post_id=post_id,
                                 url=f"https://www.linkedin.com/feed/update/{post_id}")
        return PublishResult(Platform.LINKEDIN, False, error=resp.text)


# ── INSTAGRAM / FACEBOOK ──────────────────────────────────
class InstagramPublisher(BasePublisher):
    """
    Conectar: developers.facebook.com → Create App → Instagram Graph API
    Permisos necesarios: instagram_content_publish, pages_manage_posts
    Variables de entorno: META_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID
    """

    def is_configured(self) -> bool:
        return bool(os.getenv("META_ACCESS_TOKEN") and os.getenv("INSTAGRAM_ACCOUNT_ID"))

    async def publish(self, content: str, media_url: str | None = None) -> PublishResult:
        if not self.is_configured():
            return PublishResult(Platform.INSTAGRAM, False, error="Credenciales no configuradas")

        token = os.getenv("META_ACCESS_TOKEN")
        account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")

        async with httpx.AsyncClient() as client:
            # Paso 1: crear media container
            container_resp = await client.post(
                f"https://graph.facebook.com/v19.0/{account_id}/media",
                params={
                    "caption": content,
                    "image_url": media_url or "",
                    "access_token": token,
                },
            )
            if container_resp.status_code != 200:
                return PublishResult(Platform.INSTAGRAM, False, error=container_resp.text)

            container_id = container_resp.json().get("id")

            # Paso 2: publicar
            publish_resp = await client.post(
                f"https://graph.facebook.com/v19.0/{account_id}/media_publish",
                params={"creation_id": container_id, "access_token": token},
            )

        if publish_resp.status_code == 200:
            post_id = publish_resp.json().get("id", "")
            return PublishResult(Platform.INSTAGRAM, True, post_id=post_id)
        return PublishResult(Platform.INSTAGRAM, False, error=publish_resp.text)


# ── REGISTRY ──────────────────────────────────────────────
class DistributionBus:
    """Orquesta la publicación en múltiples plataformas."""

    def __init__(self):
        self.publishers: dict[Platform, BasePublisher] = {
            Platform.LINKEDIN: LinkedInPublisher(),
            Platform.INSTAGRAM: InstagramPublisher(),
        }

    def available_platforms(self) -> list[Platform]:
        return [p for p, pub in self.publishers.items() if pub.is_configured()]

    def pending_setup(self) -> list[Platform]:
        return [p for p, pub in self.publishers.items() if not pub.is_configured()]

    async def publish_all(self, content: str, platforms: list[Platform] | None = None,
                          media_url: str | None = None) -> list[PublishResult]:
        targets = platforms or self.available_platforms()
        results = []
        for platform in targets:
            if platform in self.publishers:
                result = await self.publishers[platform].publish(content, media_url)
                results.append(result)
        return results


# Instancia global
distribution_bus = DistributionBus()
