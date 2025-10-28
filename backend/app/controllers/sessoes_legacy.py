"""
Legacy functions for sessoes module.
Contains deprecated endpoints for backwards compatibility.
"""

import logging
from typing import Union

from app.controllers.sessoes_helpers import _get_user_service
from flask import Blueprint, jsonify, request
from werkzeug.wrappers.response import Response

logger = logging.getLogger(__name__)

# Import the blueprint from sessoes_controller instead of creating a new one
from app.controllers.sessoes_controller import sessoes_bp  # noqa: E402


# DEPRECATED: Legacy endpoint - use /artist/create instead
@sessoes_bp.route("/cadastrar_artista", methods=["POST"])
def cadastrar_artista() -> tuple[Response, int]:
    """Legacy endpoint for artist creation.

    DEPRECATED: Use /artist/create_form instead.
    This is kept for backwards compatibility only.
    """
    logger.warning(
        "Using deprecated endpoint /sessoes/cadastrar_artista. Use /artist/create_form instead."
    )

    try:
        user_service = _get_user_service()
        nome = request.form.get("artista")

        if not nome:
            return jsonify({"error": "Nome do artista é obrigatório."}), 400

        artist = user_service.register_artist(name=nome.strip())

        return jsonify({"id": artist.id, "name": artist.name}), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in legacy cadastrar_artista: {str(e)}")
        return jsonify({"error": "Erro interno do servidor."}), 500
