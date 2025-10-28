import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.db.base import (
    Client,
    Comissao,
    Extrato,
    Gasto,
    Inventory,
    Pagamento,
    Sessao,
    User,
)
from sqlalchemy import and_, desc, extract, or_, text
from sqlalchemy.orm import Session


class SearchService:
    """Service for performing global search across multiple tables."""

    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search across all relevant tables with unified date ordering.

        Args:
            query: The search query string

        Returns:
            Dict with keys for each entity type and 'all_results_sorted'
            Results are sorted by date descending (newest first)
        """
        # Sanitize and normalize query
        query = self._normalize_query(query)

        results = {
            "pagamentos": [],
            "sessoes": [],
            "comissoes": [],
            "extratos": [],
            "gastos": [],
            "inventory": [],
        }

        # Search all entity types with AND logic first
        results["pagamentos"] = self._search_pagamentos(query, "and")
        results["sessoes"] = self._search_sessoes(query, "and")
        results["comissoes"] = self._search_comissoes(query, "and")
        results["extratos"] = self._search_extratos(query, "and")
        results["gastos"] = self._search_gastos(query, "and")
        results["inventory"] = self._search_inventory(query, "and")

        # Check if we have any results
        total_results = sum(
            len(v) for k, v in results.items() if k != "all_results_sorted"
        )

        # If no results with AND logic, try OR logic as fallback
        if total_results == 0 and query:
            results["pagamentos"] = self._search_pagamentos(query, "or")
            results["sessoes"] = self._search_sessoes(query, "or")
            results["comissoes"] = self._search_comissoes(query, "or")
            results["extratos"] = self._search_extratos(query, "or")
            results["gastos"] = self._search_gastos(query, "or")
            results["inventory"] = self._search_inventory(query, "or")

        # Create unified list with all results sorted by date (newest first)
        all_results = []
        for category, items in results.items():
            if category != "all_results_sorted":
                all_results.extend(items)

        # Sort all results by date descending (newest first)
        all_results.sort(key=lambda x: self._extract_date_for_sorting(x), reverse=True)
        results["all_results_sorted"] = all_results

        return results

    def _normalize_query(self, query: str) -> str:
        """Normalize query string: lowercase, strip, remove accents."""
        if not query:
            return ""

        # Strip whitespace
        query = query.strip().lower()

        # Remove accents (comprehensive implementation)
        accents = {
            "á": "a",
            "à": "a",
            "â": "a",
            "ã": "a",
            "ä": "a",
            "å": "a",
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
            "ý": "y",
            "ÿ": "y",
            "Á": "a",
            "À": "a",
            "Â": "a",
            "Ã": "a",
            "Ä": "a",
            "Å": "a",
            "É": "e",
            "È": "e",
            "Ê": "e",
            "Ë": "e",
            "Í": "i",
            "Ì": "i",
            "Î": "i",
            "Ï": "i",
            "Ó": "o",
            "Ò": "o",
            "Ô": "o",
            "Õ": "o",
            "Ö": "o",
            "Ú": "u",
            "Ù": "u",
            "Û": "u",
            "Ü": "u",
            "Ç": "c",
            "Ñ": "n",
            "Ý": "y",
            "Ÿ": "y",
        }

        for accented, normal in accents.items():
            query = query.replace(accented, normal)

        return query

    def _normalize_text(self, input_text: str) -> str:
        """Normalize any text string: lowercase, remove accents."""
        if not input_text:
            return ""

        # Convert to lowercase
        normalized = input_text.lower()

        # Remove accents
        accents = {
            "á": "a",
            "à": "a",
            "â": "a",
            "ã": "a",
            "ä": "a",
            "å": "a",
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
            "ý": "y",
            "ÿ": "y",
            "Á": "a",
            "À": "a",
            "Â": "a",
            "Ã": "a",
            "Ä": "a",
            "Å": "a",
            "É": "e",
            "È": "e",
            "Ê": "e",
            "Ë": "e",
            "Í": "i",
            "Ì": "i",
            "Î": "i",
            "Ï": "i",
            "Ó": "o",
            "Ò": "o",
            "Ô": "o",
            "Õ": "o",
            "Ö": "o",
            "Ú": "u",
            "Ù": "u",
            "Û": "u",
            "Ü": "u",
            "Ç": "c",
            "Ñ": "n",
            "Ý": "y",
            "Ÿ": "y",
        }

        for accented, normal in accents.items():
            normalized = normalized.replace(accented, normal)

        return normalized

    def _parse_query(
        self, query: str
    ) -> Tuple[List[str], Optional[datetime], Optional[Tuple[int, int]]]:
        """Parse query into tokens, exact date, and day/month filters.

        Returns:
            Tuple of (tokens, exact_date, day_month_tuple)
            - tokens: List of search terms (excluding dates)
            - exact_date: datetime object if dd/mm/yyyy format found
            - day_month_tuple: (day, month) tuple if dd/mm format found
        """
        if not query:
            return [], None, None

        # Split query into potential tokens
        raw_tokens = re.split(r"\s+", query.strip())

        tokens = []
        exact_date = None
        day_month = None

        # Date patterns
        date_dd_mm_yyyy = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
        date_yyyy_mm_dd = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
        date_dd_mm = re.compile(r"^(\d{1,2})/(\d{1,2})$")

        for token in raw_tokens:
            # Check for dd/mm/yyyy format
            match_yyyy = date_dd_mm_yyyy.match(token)
            if match_yyyy:
                try:
                    day, month, year = map(int, match_yyyy.groups())
                    exact_date = datetime(year, month, day)
                    continue
                except ValueError:
                    pass

            # Check for yyyy-mm-dd format
            match_iso = date_yyyy_mm_dd.match(token)
            if match_iso:
                try:
                    year, month, day = map(int, match_iso.groups())
                    exact_date = datetime(year, month, day)
                    continue
                except ValueError:
                    pass

            # Check for dd/mm format
            match_mm = date_dd_mm.match(token)
            if match_mm:
                try:
                    day, month = map(int, match_mm.groups())
                    if 1 <= day <= 31 and 1 <= month <= 12:
                        day_month = (day, month)
                        continue
                except ValueError:
                    pass

            # If not a date, add as search token
            tokens.append(token)

        return tokens, exact_date, day_month

    def _build_text_filters(self, tokens: List[str], *fields) -> List:
        """Build SQLAlchemy filters for text search across multiple fields.

        Each token must be found in at least one of the fields.
        """
        if not tokens:
            return []

        filters = []
        for token in tokens:
            token_filters = []
            for field in fields:
                token_filters.append(field.ilike(f"%{token}%"))
            if token_filters:
                filters.append(or_(*token_filters))

        return filters

    def _build_combined_filters(
        self, tokens: List[str], text_fields, numeric_fields=None, logic: str = "and"
    ) -> List:
        """Build SQLAlchemy filters for both text and numeric fields.

        Args:
            tokens: Search tokens
            text_fields: Text fields to search
            numeric_fields: Numeric fields to search (cast to string)
            logic: "and" or "or" - whether all tokens must match or any token

        Returns:
            List of SQLAlchemy filter expressions
        """
        if not tokens:
            return []

        filters = []

        for token in tokens:
            token_filters = []

            # Add text field filters
            for field in text_fields:
                token_filters.append(field.ilike(f"%{token}%"))

            # Add numeric field filters (cast to string for matching)
            if numeric_fields:
                for field in numeric_fields:
                    # Cast numeric field to string and search
                    from sqlalchemy import String, cast

                    token_filters.append(cast(field, String).ilike(f"%{token}%"))

            if token_filters:
                filters.append(or_(*token_filters))

        # Combine filters based on logic
        if logic == "or":
            return [or_(*filters)] if filters else []
        else:  # and
            return filters

    def _build_date_filters(
        self,
        exact_date: Optional[datetime],
        day_month: Optional[Tuple[int, int]],
        date_field,
    ) -> List:
        """Build SQLAlchemy filters for date matching."""
        filters = []

        if exact_date:
            # Exact date match
            filters.append(date_field == exact_date.date())

        elif day_month:
            # Day and month match (any year)
            day, month = day_month
            filters.append(extract("day", date_field) == day)
            filters.append(extract("month", date_field) == month)

        return filters

    def _search_pagamentos(
        self, query: str, logic: str = "and"
    ) -> List[Dict[str, Any]]:
        """Search pagamentos table with enhanced token and date search."""
        if not query:
            return []

        # Parse query into tokens and date filters
        tokens, exact_date, day_month = self._parse_query(query)

        # Build filters for text and numeric fields
        text_fields = [
            User.name,
            Pagamento.observacoes,
            Pagamento.forma_pagamento,
        ]
        numeric_fields = [Pagamento.valor]

        combined_filters = self._build_combined_filters(
            tokens, text_fields, numeric_fields, logic
        )

        # Add client name filters with NULL safety - match client name OR allow NULL clients
        for token in tokens:
            # This filter will match payments where:
            # 1. The client name contains the token, OR
            # 2. There is no client (cliente_id is NULL)
            # This way we don't exclude payments without clients from search results
            client_filter = or_(Client.name.ilike(f"%{token}%"), Client.name.is_(None))
            combined_filters.append(client_filter)

        date_filters = self._build_date_filters(exact_date, day_month, Pagamento.data)

        # Combine all filters
        all_filters = combined_filters + date_filters

        if not all_filters:
            return []

        pagamentos = (
            self.db.query(Pagamento)
            .outerjoin(Client, Pagamento.cliente_id == Client.id)
            .join(User, Pagamento.artista_id == User.id)
            .filter(and_(*all_filters))
            .order_by(desc(Pagamento.data))
            .all()
        )

        return [
            {
                "id": p.id,
                "data": p.data.isoformat() if p.data else None,  # type: ignore
                "valor": float(p.valor) if p.valor else 0,  # type: ignore
                "forma_pagamento": p.forma_pagamento,
                "observacoes": p.observacoes,
                "cliente_name": p.cliente.name if p.cliente else "",
                "artista_name": p.artista.name if p.artista else "",
                "source": "pagamento",
                "entity_type": "Pagamento",
            }
            for p in pagamentos
        ]

    def _search_sessoes(self, query: str, logic: str = "and") -> List[Dict[str, Any]]:
        """Search sessoes table with enhanced token and date search."""
        if not query:
            return []

        # Parse query into tokens and date filters
        tokens, exact_date, day_month = self._parse_query(query)

        # Build filters for text and numeric fields
        text_fields = [Client.name, User.name, Sessao.observacoes]
        numeric_fields = [Sessao.valor]

        combined_filters = self._build_combined_filters(
            tokens, text_fields, numeric_fields, logic
        )

        date_filters = self._build_date_filters(exact_date, day_month, Sessao.data)

        # Combine all filters
        all_filters = combined_filters + date_filters

        if not all_filters:
            return []

        sessoes = (
            self.db.query(Sessao)
            .join(Client, Sessao.cliente_id == Client.id)
            .join(User, Sessao.artista_id == User.id)
            .filter(and_(*all_filters))
            .order_by(desc(Sessao.data))
            .all()
        )

        return [
            {
                "id": s.id,
                "data": s.data.isoformat() if s.data else None,  # type: ignore
                "valor": float(s.valor) if s.valor else 0,  # type: ignore
                "observacoes": s.observacoes,
                "status": s.status,
                "cliente_name": s.cliente.name if s.cliente else "",
                "artista_name": s.artista.name if s.artista else "",
                "source": "sessao",
                "entity_type": "Sessão",
            }
            for s in sessoes
        ]

    def _search_comissoes(self, query: str, logic: str = "and") -> List[Dict[str, Any]]:
        """Search comissoes table with enhanced token and date search."""
        if not query:
            return []

        # Parse query into tokens and date filters
        tokens, exact_date, day_month = self._parse_query(query)

        # Build filters for text and numeric fields
        text_fields = [User.name, Comissao.observacoes]
        numeric_fields = [Comissao.percentual, Comissao.valor]

        combined_filters = self._build_combined_filters(
            tokens, text_fields, numeric_fields, logic
        )

        date_filters = self._build_date_filters(
            exact_date, day_month, Comissao.created_at
        )

        # Combine all filters
        all_filters = combined_filters + date_filters

        if not all_filters:
            return []

        comissoes = (
            self.db.query(Comissao)
            .join(User, Comissao.artista_id == User.id)
            .filter(and_(*all_filters))
            .order_by(desc(Comissao.created_at))
            .all()
        )

        return [
            {
                "id": c.id,
                "percentual": float(c.percentual) if c.percentual else 0,  # type: ignore
                "valor": float(c.valor) if c.valor else 0,  # type: ignore
                "observacoes": c.observacoes,
                "artista_name": c.artista.name if c.artista else "",
                "pagamento_id": c.pagamento_id,
                "data": c.created_at.date().isoformat() if c.created_at else None,  # type: ignore
                "source": "comissao",
                "entity_type": "Comissão",
            }
            for c in comissoes
        ]

    def _search_extratos(self, query: str, logic: str = "and") -> List[Dict[str, Any]]:
        """Search extratos table (JSON data) with enhanced token and date search."""
        if not query:
            return []

        # Parse query into tokens and date filters
        tokens, exact_date, day_month = self._parse_query(query)

        # For extratos, we need to search within the JSON arrays
        # This is a simplified approach - load all extratos and search in Python
        extratos = self.db.query(Extrato).all()

        results = []
        for e in extratos:
            matches = []

            # Search in pagamentos JSON
            if e.pagamentos:  # type: ignore
                for p in e.pagamentos:
                    if self._json_contains_tokens_and_date(p, tokens, exact_date, day_month, logic):  # type: ignore
                        matches.append(
                            {"type": "pagamento", "data": p, "mes": e.mes, "ano": e.ano}
                        )

            # Search in sessoes JSON
            if e.sessoes:  # type: ignore
                for s in e.sessoes:
                    if self._json_contains_tokens_and_date(s, tokens, exact_date, day_month, logic):  # type: ignore
                        matches.append(
                            {"type": "sessao", "data": s, "mes": e.mes, "ano": e.ano}
                        )

            # Search in comissoes JSON
            if e.comissoes:  # type: ignore
                for c in e.comissoes:
                    if self._json_contains_tokens_and_date(c, tokens, exact_date, day_month, logic):  # type: ignore
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

    def _flatten_json_to_text(self, obj: Any) -> str:
        """Flatten a JSON object to a searchable text string."""
        if obj is None:
            return ""
        elif isinstance(obj, str):
            return obj
        elif isinstance(obj, (int, float)):
            return str(obj)
        elif isinstance(obj, bool):
            return str(obj).lower()
        elif isinstance(obj, list):
            return " ".join(self._flatten_json_to_text(item) for item in obj)
        elif isinstance(obj, dict):
            parts = []
            for key, value in obj.items():
                parts.append(str(key))
                parts.append(self._flatten_json_to_text(value))
            return " ".join(parts)
        else:
            return str(obj)

    def _json_contains_tokens_and_date(
        self,
        json_obj: Dict[str, Any],
        tokens: List[str],
        exact_date: Optional[datetime],
        day_month: Optional[Tuple[int, int]],
        logic: str = "and",
    ) -> bool:
        """Check if JSON object contains tokens and matches date criteria."""
        if not json_obj or not isinstance(json_obj, dict):
            return False

        # Flatten JSON to text and normalize
        json_text = self._flatten_json_to_text(json_obj)
        normalized_json = self._normalize_text(json_text)

        # Check tokens
        if tokens:
            normalized_tokens = [self._normalize_text(token) for token in tokens]
            if logic == "or":
                # Any token must be present
                if not any(token in normalized_json for token in normalized_tokens):
                    return False
            else:  # and
                # All tokens must be present
                if not all(token in normalized_json for token in normalized_tokens):
                    return False

        # Check date criteria
        if exact_date or day_month:
            # Try to extract date from JSON object
            date_str = (
                json_obj.get("data")
                or json_obj.get("created_at")
                or json_obj.get("date")
            )
            if date_str:
                try:
                    parsed_date = None
                    if isinstance(date_str, str):
                        # Try different date formats
                        for fmt in [
                            "%Y-%m-%d",
                            "%d/%m/%Y",
                            "%Y-%m-%dT%H:%M:%S",
                            "%Y-%m-%d %H:%M:%S",
                            "%d/%m/%Y %H:%M:%S",
                        ]:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                continue
                        else:
                            # Try to parse just date part if it contains time
                            date_part = (
                                date_str.split(" ")[0] if " " in date_str else date_str
                            )
                            for fmt in ["%Y-%m-%d", "%d/%m/%Y"]:
                                try:
                                    parsed_date = datetime.strptime(
                                        date_part, fmt
                                    ).date()
                                    break
                                except ValueError:
                                    continue
                            else:
                                return False  # No valid date format found
                    elif hasattr(date_str, "date"):
                        parsed_date = date_str.date()
                    elif isinstance(date_str, datetime):
                        parsed_date = date_str.date()
                    else:
                        return False

                    if parsed_date:
                        # Check exact date match
                        if exact_date and parsed_date == exact_date.date():
                            return True

                        # Check day/month match
                        if day_month:
                            day, month = day_month
                            if parsed_date.day == day and parsed_date.month == month:
                                return True

                    return False

                except (ValueError, AttributeError):
                    return False

        # If no date criteria, just check tokens
        return True

    def _search_gastos(self, query: str, logic: str = "and") -> List[Dict[str, Any]]:
        """Search gastos (expenses) table with enhanced token and date search."""
        if not query:
            return []

        # Parse query into tokens and date filters
        tokens, exact_date, day_month = self._parse_query(query)

        # Build filters for text and numeric fields
        text_fields = [User.name, Gasto.descricao, Gasto.forma_pagamento]
        numeric_fields = [Gasto.valor]

        combined_filters = self._build_combined_filters(
            tokens, text_fields, numeric_fields, logic
        )

        date_filters = self._build_date_filters(exact_date, day_month, Gasto.data)

        # Combine all filters
        all_filters = combined_filters + date_filters

        if not all_filters:
            return []

        gastos = (
            self.db.query(Gasto)
            .join(User, Gasto.created_by == User.id)
            .filter(and_(*all_filters))
            .order_by(desc(Gasto.data))
            .all()
        )

        return [
            {
                "id": g.id,
                "data": g.data.isoformat() if g.data else None,  # type: ignore
                "valor": float(g.valor) if g.valor else 0,  # type: ignore
                "descricao": g.descricao,
                "forma_pagamento": g.forma_pagamento,
                "created_by_name": g.creator.name if g.creator else "",
                "source": "gasto",
                "entity_type": "Gasto",
            }
            for g in gastos
        ]

    def _search_inventory(self, query: str, logic: str = "and") -> List[Dict[str, Any]]:
        """Search inventory table with enhanced token and date search."""
        if not query:
            return []

        # Parse query into tokens and date filters
        tokens, exact_date, day_month = self._parse_query(query)

        # Build filters for text and numeric fields
        text_fields = [
            Inventory.nome,
            Inventory.observacoes,
            Inventory.category,
            Inventory.supplier,
        ]
        numeric_fields = [Inventory.quantidade, Inventory.unit_price]

        combined_filters = self._build_combined_filters(
            tokens, text_fields, numeric_fields, logic
        )

        date_filters = self._build_date_filters(
            exact_date, day_month, Inventory.updated_at
        )

        # Combine all filters
        all_filters = combined_filters + date_filters

        if not all_filters:
            return []

        inventory_items = (
            self.db.query(Inventory)
            .filter(and_(*all_filters))
            .order_by(desc(Inventory.updated_at))
            .all()
        )

        return [
            {
                "id": i.id,
                "nome": i.nome,
                "quantidade": i.quantidade,
                "observacoes": i.observacoes,
                "category": i.category,
                "unit_price": float(i.unit_price) if i.unit_price else 0,  # type: ignore
                "supplier": i.supplier,
                "data": i.updated_at.date().isoformat() if i.updated_at else None,  # type: ignore
                "source": "inventory",
                "entity_type": "Estoque",
            }
            for i in inventory_items
        ]

    def _extract_date_for_sorting(self, result: Dict[str, Any]) -> datetime:
        """Extract date from result for sorting purposes."""
        # Try to get the date field
        date_str = result.get("data")
        if date_str:
            try:
                return datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                pass

        # Fallback for extratos - use year/month
        if result.get("source") == "extrato":
            ano = result.get("ano", 2000)
            mes = result.get("mes", 1)
            try:
                return datetime(ano, mes, 1)
            except (ValueError, TypeError):
                pass

        # Default to a very old date for items without dates
        return datetime(1900, 1, 1)
