#!/usr/bin/env python3
"""
Seed script para inserir dados fictícios de extrato para testes manuais.
Cria dados de sessões, pagamentos e comissões para o mês anterior.

Uso: python backend/scripts/seed_fake_extrato_data.py
"""

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from app.core.logging_config import get_logger

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Client, Comissao, Pagamento, Sessao, User
from app.db.session import SessionLocal

logger = get_logger(__name__)


def get_previous_month():
    """Calcula o mês anterior."""
    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    return last_day_prev_month.month, last_day_prev_month.year


def create_fake_users_and_clients(db):
    """Cria ou recupera usuários (artistas) e clientes fictícios."""

    # Criar/recuperar artistas

    artista1 = db.query(User).filter(User.email == "pedro.artista@teste.com").first()
    if not artista1:
        artista1 = User()
        artista1.email = "pedro.artista@teste.com"
        artista1.name = "Pedro Artista"
        artista1.role = "artist"
        db.add(artista1)

    artista2 = db.query(User).filter(User.email == "maria.artista@teste.com").first()
    if not artista2:
        artista2 = User()
        artista2.email = "maria.artista@teste.com"
        artista2.name = "Maria Artista"
        artista2.role = "artist"
        db.add(artista2)

    # Criar/recuperar clientes
    cliente1 = (
        db.query(Client).filter(Client.jotform_submission_id == "fake_sub_001").first()
    )
    if not cliente1:
        cliente1 = Client(name="Ana Cliente", jotform_submission_id="fake_sub_001")
        db.add(cliente1)

    cliente2 = (
        db.query(Client).filter(Client.jotform_submission_id == "fake_sub_002").first()
    )
    if not cliente2:
        cliente2 = Client(name="João Cliente", jotform_submission_id="fake_sub_002")
        db.add(cliente2)

    cliente3 = (
        db.query(Client).filter(Client.jotform_submission_id == "fake_sub_003").first()
    )
    if not cliente3:
        cliente3 = Client(name="Carla Cliente", jotform_submission_id="fake_sub_003")
        db.add(cliente3)

    db.commit()
    db.refresh(artista1)
    db.refresh(artista2)
    db.refresh(cliente1)
    db.refresh(cliente2)
    db.refresh(cliente3)

    return [artista1, artista2], [cliente1, cliente2, cliente3]


def create_fake_sessoes(db, mes, ano, artistas, clientes):
    """Cria 3 sessões fictícias para o mês anterior."""

    # Datas do mês anterior
    sessao1_date = datetime(ano, mes, 5).date()
    sessao2_date = datetime(ano, mes, 15).date()
    sessao3_date = datetime(ano, mes, 25).date()

    sessoes = []

    # Sessão 1
    sessao1 = Sessao(
        data=sessao1_date,
        valor=Decimal("450.00"),
        observacoes="Sessão de tatuagem - braço completo",
        cliente_id=clientes[0].id,
        artista_id=artistas[0].id,
        status="completed",
    )
    sessoes.append(sessao1)

    # Sessão 2
    sessao2 = Sessao(
        data=sessao2_date,
        valor=Decimal("320.00"),
        observacoes="Sessão de tatuagem - perna",
        cliente_id=clientes[1].id,
        artista_id=artistas[1].id,
        status="completed",
    )
    sessoes.append(sessao2)

    # Sessão 3
    sessao3 = Sessao(
        data=sessao3_date,
        valor=Decimal("280.00"),
        observacoes="Sessão de tatuagem - costas",
        cliente_id=clientes[2].id,
        artista_id=artistas[0].id,
        status="completed",
    )
    sessoes.append(sessao3)

    for sessao in sessoes:
        db.add(sessao)

    db.commit()

    for sessao in sessoes:
        db.refresh(sessao)

    return sessoes


def create_fake_pagamentos(db, sessoes):
    """Cria 3 pagamentos vinculados às sessões."""

    pagamentos = []
    formas_pagamento = ["Pix", "Cartão", "Dinheiro"]

    for i, sessao in enumerate(sessoes):
        pagamento = Pagamento(
            data=sessao.data,
            valor=sessao.valor,
            forma_pagamento=formas_pagamento[i],
            observacoes=f"Pagamento referente à sessão {sessao.id}",
            cliente_id=sessao.cliente_id,
            artista_id=sessao.artista_id,
            sessao_id=sessao.id,
        )
        pagamentos.append(pagamento)
        db.add(pagamento)

    db.commit()

    for pagamento in pagamentos:
        db.refresh(pagamento)

    return pagamentos


def create_fake_comissoes(db, pagamentos):
    """Cria 3 comissões vinculadas aos pagamentos."""

    comissoes = []
    percentuais = [
        Decimal("30.00"),
        Decimal("25.00"),
        Decimal("35.00"),
    ]  # Percentuais variados

    for i, pagamento in enumerate(pagamentos):
        percentual = percentuais[i]
        valor_comissao = pagamento.valor * (percentual / 100)

        comissao = Comissao(
            pagamento_id=pagamento.id,
            artista_id=pagamento.artista_id,
            percentual=percentual,
            valor=valor_comissao,
            observacoes=f"Comissão de {percentual}% sobre pagamento {pagamento.id}",
        )
        comissoes.append(comissao)
        db.add(comissao)

    db.commit()

    for comissao in comissoes:
        db.refresh(comissao)

    return comissoes


def main():
    """Função principal para executar o seeding."""

    logger.info("Iniciando seed de dados fictícios para extrato")

    # Calcular mês anterior
    mes, ano = get_previous_month()
    logger.info("Criando dados", extra={"context": {"mes": mes, "ano": ano}})

    db = SessionLocal()
    try:
        # 1. Criar usuários e clientes fictícios
        logger.info("Criando usuários e clientes fictícios")
        artistas, clientes = create_fake_users_and_clients(db)
        logger.info(
            "Criados/recuperados usuários e clientes",
            extra={"context": {"artistas": len(artistas), "clientes": len(clientes)}},
        )

        # 2. Criar sessões
        logger.info("Criando sessões fictícias")
        sessoes = create_fake_sessoes(db, mes, ano, artistas, clientes)
        logger.info("Sessões criadas", extra={"context": {"count": len(sessoes)}})

        # 3. Criar pagamentos
        logger.info("Criando pagamentos fictícios")
        pagamentos = create_fake_pagamentos(db, sessoes)
        logger.info("Pagamentos criados", extra={"context": {"count": len(pagamentos)}})

        # 4. Criar comissões
        logger.info("Criando comissões fictícias")
        comissoes = create_fake_comissoes(db, pagamentos)
        logger.info("Comissões criadas", extra={"context": {"count": len(comissoes)}})

        # Resumo dos dados criados
        logger.info(
            "Resumo dos dados criados", extra={"context": {"delimiter": "=" * 50}}
        )

        for i, (sessao, pagamento, comissao) in enumerate(
            zip(sessoes, pagamentos, comissoes), 1
        ):
            logger.info(
                "Registro criado",
                extra={
                    "context": {
                        "indice": i,
                        "sessao": {
                            "data": str(sessao.data),
                            "artista": getattr(
                                getattr(sessao, "artista", None), "name", None
                            ),
                            "valor": str(sessao.valor),
                        },
                        "cliente": getattr(
                            getattr(sessao, "cliente", None), "name", None
                        ),
                        "pagamento": {
                            "forma": pagamento.forma_pagamento,
                            "valor": str(pagamento.valor),
                        },
                        "comissao": {
                            "percentual": str(comissao.percentual),
                            "valor": str(comissao.valor),
                        },
                    }
                },
            )

        total_receita = sum(p.valor for p in pagamentos)
        total_comissoes = sum(c.valor for c in comissoes)

        logger.info(
            "Totais",
            extra={
                "context": {
                    "receita": str(total_receita),
                    "comissoes": str(total_comissoes),
                }
            },
        )

        logger.info(
            "Dados fictícios criados com sucesso",
            extra={"context": {"mes": mes, "ano": ano}},
        )
        logger.info("Agora você pode testar a página de extrato com dados reais")
        logger.info(
            "Para gerar o extrato",
            extra={
                "context": {
                    "command": f"python backend/scripts/generate_monthly_extrato.py --mes {mes} --ano {ano} --force"
                }
            },
        )

    except Exception as e:
        db.rollback()
        logger.error(
            "Erro ao criar dados fictícios",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
