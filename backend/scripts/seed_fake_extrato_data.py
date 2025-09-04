#!/usr/bin/env python3
"""
Seed script para inserir dados fictícios de extrato para testes manuais.
Cria dados de sessões, pagamentos e comissões para o mês anterior.

Uso: python backend/scripts/seed_fake_extrato_data.py
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import SessionLocal
from app.db.base import User, Client, Sessao, Pagamento, Comissao


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
        artista1 = User(
            email="pedro.artista@teste.com",
            name="Pedro Artista",
            role="artist",
            is_active=True,
        )
        db.add(artista1)

    artista2 = db.query(User).filter(User.email == "maria.artista@teste.com").first()
    if not artista2:
        artista2 = User(
            email="maria.artista@teste.com",
            name="Maria Artista",
            role="artist",
            is_active=True,
        )
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
        hora=datetime.strptime("14:00", "%H:%M").time(),
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
        hora=datetime.strptime("16:30", "%H:%M").time(),
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
        hora=datetime.strptime("10:00", "%H:%M").time(),
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

    print("🌱 Iniciando seed de dados fictícios para extrato...")

    # Calcular mês anterior
    mes, ano = get_previous_month()
    print(f"📅 Criando dados para: {mes:02d}/{ano}")

    db = SessionLocal()
    try:
        # 1. Criar usuários e clientes fictícios
        print("👥 Criando usuários e clientes fictícios...")
        artistas, clientes = create_fake_users_and_clients(db)
        print(
            f"   ✅ Criados/recuperados {len(artistas)} artistas e {len(clientes)} clientes"
        )

        # 2. Criar sessões
        print("📝 Criando sessões fictícias...")
        sessoes = create_fake_sessoes(db, mes, ano, artistas, clientes)
        print(f"   ✅ Criadas {len(sessoes)} sessões")

        # 3. Criar pagamentos
        print("💰 Criando pagamentos fictícios...")
        pagamentos = create_fake_pagamentos(db, sessoes)
        print(f"   ✅ Criados {len(pagamentos)} pagamentos")

        # 4. Criar comissões
        print("🎯 Criando comissões fictícias...")
        comissoes = create_fake_comissoes(db, pagamentos)
        print(f"   ✅ Criadas {len(comissoes)} comissões")

        # Resumo dos dados criados
        print("\n📊 Resumo dos dados criados:")
        print("=" * 50)

        for i, (sessao, pagamento, comissao) in enumerate(
            zip(sessoes, pagamentos, comissoes), 1
        ):
            print(f"\n🔸 Registro {i}:")
            print(
                f"   Sessão: {sessao.data} - {artistas[sessao.artista_id-artistas[0].id].name} - R$ {sessao.valor}"
            )
            print(f"   Cliente: {clientes[sessao.cliente_id-clientes[0].id].name}")
            print(f"   Pagamento: {pagamento.forma_pagamento} - R$ {pagamento.valor}")
            print(f"   Comissão: {comissao.percentual}% - R$ {comissao.valor}")

        total_receita = sum(p.valor for p in pagamentos)
        total_comissoes = sum(c.valor for c in comissoes)

        print(f"\n💵 Total receita: R$ {total_receita}")
        print(f"🎯 Total comissões: R$ {total_comissoes}")

        print(f"\n✅ Dados fictícios criados com sucesso para {mes:02d}/{ano}!")
        print("🔍 Agora você pode testar a página de extrato com dados reais.")
        print(
            f"💡 Para gerar o extrato, execute: python backend/scripts/generate_monthly_extrato.py --mes {mes} --ano {ano} --force"
        )

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar dados fictícios: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
