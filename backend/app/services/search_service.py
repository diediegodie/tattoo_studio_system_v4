from typing import List, Dict, Any
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
from app.db.base import Pagamento, Sessao, Comissao, Extrato, Client, User


class SearchService:
    """Service for performing global search across multiple tables."""

    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search across pagamentos, sessoes, comissoes, and extratos.

        Args:
            query: The search query string

        Returns:
            Dict with keys 'pagamentos', 'sessoes', 'comissoes', 'extratos'
            Each containing a list of matching records
        """
        # Sanitize and normalize query
        query = self._normalize_query(query)

        results = {"pagamentos": [], "sessoes": [], "comissoes": [], "extratos": []}

        # Search pagamentos
        results["pagamentos"] = self._search_pagamentos(query)

        # Search sessoes
        results["sessoes"] = self._search_sessoes(query)

        # Search comissoes
        results["comissoes"] = self._search_comissoes(query)

        # Search extratos (JSON data)
        results["extratos"] = self._search_extratos(query)

        return results

    def _normalize_query(self, query: str) -> str:
        """Normalize query string: lowercase, strip, remove accents."""
        if not query:
            return ""

        # Strip whitespace
        query = query.strip().lower()

        # Remove accents (basic implementation)
        accents = {
            "á": "a",
            "à": "a",
            "â": "a",
            "ã": "a",
            "ä": "a",
            "é": "e",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "í": "i",
            "ì": "i",
            "î": "i",
            "ï": "i",
            "ó": "o",
            "ò": "o",
            "ô": "o",
            "õ": "o",
            "ö": "o",
            "ú": "u",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "ç": "c",
            "ñ": "n",
        }

        for accented, normal in accents.items():
            query = query.replace(accented, normal)

        return query

    def _search_pagamentos(self, query: str) -> List[Dict[str, Any]]:
        """Search pagamentos table."""
        if not query:
            return []

        pagamentos = (
            self.db.query(Pagamento)
            .join(Client, Pagamento.cliente_id == Client.id)
            .join(User, Pagamento.artista_id == User.id)
            .filter(
                or_(
                    Client.name.ilike(f"%{query}%"),
                    User.name.ilike(f"%{query}%"),
                    Pagamento.observacoes.ilike(f"%{query}%"),
                )
            )
            .all()
        )

        return [
            {
                "id": p.id,
                "data": p.data.isoformat() if p.data else None,
                "valor": float(p.valor) if p.valor else 0,
                "forma_pagamento": p.forma_pagamento,
                "observacoes": p.observacoes,
                "cliente_name": p.cliente.name if p.cliente else "",
                "artista_name": p.artista.name if p.artista else "",
                "source": "pagamento",
            }
            for p in pagamentos
        ]

    def _search_sessoes(self, query: str) -> List[Dict[str, Any]]:
        """Search sessoes table."""
        if not query:
            return []

        sessoes = (
            self.db.query(Sessao)
            .join(Client, Sessao.cliente_id == Client.id)
            .join(User, Sessao.artista_id == User.id)
            .filter(
                or_(
                    Client.name.ilike(f"%{query}%"),
                    User.name.ilike(f"%{query}%"),
                    Sessao.observacoes.ilike(f"%{query}%"),
                )
            )
            .all()
        )

        return [
            {
                "id": s.id,
                "data": s.data.isoformat() if s.data else None,
                "hora": str(s.hora) if s.hora else "",
                "valor": float(s.valor) if s.valor else 0,
                "observacoes": s.observacoes,
                "status": s.status,
                "cliente_name": s.cliente.name if s.cliente else "",
                "artista_name": s.artista.name if s.artista else "",
                "source": "sessao",
            }
            for s in sessoes
        ]

    def _search_comissoes(self, query: str) -> List[Dict[str, Any]]:
        """Search comissoes table."""
        if not query:
            return []

        comissoes = (
            self.db.query(Comissao)
            .join(User, Comissao.artista_id == User.id)
            .filter(
                or_(
                    User.name.ilike(f"%{query}%"),
                    Comissao.observacoes.ilike(f"%{query}%"),
                )
            )
            .all()
        )

        return [
            {
                "id": c.id,
                "percentual": float(c.percentual) if c.percentual else 0,
                "valor": float(c.valor) if c.valor else 0,
                "observacoes": c.observacoes,
                "artista_name": c.artista.name if c.artista else "",
                "pagamento_id": c.pagamento_id,
                "source": "comissao",
            }
            for c in comissoes
        ]

    def _search_extratos(self, query: str) -> List[Dict[str, Any]]:
        """Search extratos table (JSON data)."""
        if not query:
            return []

        # For extratos, we need to search within the JSON arrays
        # This is a simplified approach - load all extratos and search in Python
        extratos = self.db.query(Extrato).all()

        results = []
        for e in extratos:
            matches = []

            # Search in pagamentos JSON
            if e.pagamentos:
                for p in e.pagamentos:
                    if self._json_contains_query(p, query):
                        matches.append(
                            {"type": "pagamento", "data": p, "mes": e.mes, "ano": e.ano}
                        )

            # Search in sessoes JSON
            if e.sessoes:
                for s in e.sessoes:
                    if self._json_contains_query(s, query):
                        matches.append(
                            {"type": "sessao", "data": s, "mes": e.mes, "ano": e.ano}
                        )

            # Search in comissoes JSON
            if e.comissoes:
                for c in e.comissoes:
                    if self._json_contains_query(c, query):
                        matches.append(
                            {"type": "comissao", "data": c, "mes": e.mes, "ano": e.ano}
                        )

            if matches:
                results.append(
                    {
                        "id": e.id,
                        "mes": e.mes,
                        "ano": e.ano,
                        "matches": matches,
                        "source": "extrato",
                    }
                )

        return results

    def _json_contains_query(self, json_obj: Dict[str, Any], query: str) -> bool:
        """Check if JSON object contains the query string in key fields."""
        if not json_obj or not isinstance(json_obj, dict):
            return False

        # Convert to lowercase string for searching
        json_str = str(json_obj).lower()

        # Search for the query (also lowercase)
        return query.lower() in json_str
