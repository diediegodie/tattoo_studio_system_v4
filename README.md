# Tattoo Studio System

## Projeto
Sistema de gerenciamento para estúdio de tatuagem, com backend Flask, banco de dados PostgreSQL, autenticação Google OAuth e frontend responsivo.

## Estrutura
- **backend/**: Código Python Flask, modelos SQLAlchemy, autenticação, rotas e lógica de negócio
- **frontend/**: Templates HTML, CSS, JS, páginas do sistema
- **docker-compose.yml**: Orquestração dos serviços
- **requirements.txt**: Dependências Python
- **.env**: Variáveis de ambiente (credenciais, URLs)

## Instalação Rápida
1. Instale Docker e Docker Compose
2. **IMPORTANTE**: Copie e configure o arquivo de ambiente:
   ```bash
   cp .env.example .env
   ```
3. Edite o arquivo `.env` com suas credenciais reais:
   - Configure as credenciais do Google OAuth (veja seção abaixo)
   - Altere senhas padrão do banco de dados
   - Configure uma chave secreta segura para o Flask
4. Inicie os serviços:
   ```bash
   docker compose up -d --build
   ```
5. Acesse o sistema em `http://localhost:5000/`

## Autenticação Google OAuth
1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Habilite as APIs: Google+ API e Google Identity API
4. Configure as credenciais OAuth 2.0:
   - Tipo: Aplicação Web
   - URIs de redirecionamento autorizados:
     - `http://localhost:5000/auth/google/authorized`
     - `http://127.0.0.1:5000/auth/google/authorized`
5. Copie o Client ID e Client Secret para o arquivo `.env`

## Banco de Dados
- PostgreSQL
- Tabelas criadas automaticamente (`users`, `oauth`)
- Para consultar usuários:
	```bash
	docker compose exec db psql -U admin -d tattoo_studio -c "SELECT id, name, email FROM users;"
	```

## Principais Endpoints
- `/` ou `/login`: Página de login
- `/index`: Dashboard (protegido)
- `/auth/login`: Iniciar OAuth
- `/auth/logout`: Logout
- Outras páginas: estoque, sessões, financeiro, extrato, cadastro interno, calculadora, histórico

## Comandos Úteis
- Iniciar: `docker compose up -d --build`
- Parar: `docker compose down`
- Logs: `docker compose logs app -f`
- Consultar banco: `docker compose exec db psql -U admin -d tattoo_studio`

## Futuras Implementações
- [ ] Funcionalidades adicionais do sistema
- [ ] Integração com outros métodos de pagamento
- [ ] Relatórios e dashboards avançados
- [ ] Notificações e alertas
- [ ] Customização de permissões de usuário
- [ ] Backup e restore automatizado


---

COMANDOS DOCKER - GERENCIAMENTO COMPLETO

- INICIAR APLICAÇÃO
# Iniciar todos os serviços (app + database)
docker compose up -d --build
# Ou iniciar sem rebuild (mais rápido após primeira vez)
docker compose up -d
# Iniciar apenas o banco de dados
docker compose up -d db
# Iniciar apenas a aplicação
docker compose up -d app

- PARAR APLICAÇÃO
# Parar todos os serviços
docker compose down
# Parar e remover volumes (CUIDADO: apaga dados do banco!)
docker compose down -v
# Parar apenas a aplicação (mantém banco rodando)
docker compose stop app
# Parar apenas o banco de dados
docker compose stop db

- MONITORAMENTO E LOGS
# Ver logs da aplicação em tempo real
docker compose logs app -f
# Ver logs do banco de dados
docker compose logs db -f
# Ver logs de todos os serviços
docker compose logs -f
# Ver status dos containers
docker compose ps
# Ver status mais detalhado
docker ps

- GERENCIAMENTO DO BANCO DE DADOS
# Acessar terminal do PostgreSQL
docker compose exec db psql -U admin -d tattoo_studio
# Consultar usuários diretamente
docker compose exec db psql -U admin -d tattoo_studio -c "SELECT id, name, email FROM users;"
# Backup do banco de dados
docker compose exec db pg_dump -U admin tattoo_studio > backup.sql
# Restaurar backup
docker compose exec -T db psql -U admin -d tattoo_studio < backup.sql

- REINICIAR SERVIÇOS
# Reiniciar aplicação
docker compose restart app
# Reiniciar banco de dados
docker compose restart db
# Reiniciar todos os serviços
docker compose restart

- LIMPEZA E MANUTENÇÃO
# Rebuild completo (força reconstrução)
docker compose up -d --build --force-recreate
# Remover containers parados
docker container prune
# Remover imagens não utilizadas
docker image prune
# Limpeza completa (CUIDADO!)
docker system prune -a

- DEBUG E TROUBLESHOOTING
# Acessar terminal da aplicação
docker compose exec app bash
# Verificar variáveis de ambiente da aplicação
docker compose exec app env
# Ver recursos utilizados
docker stats
# Inspecionar container específico
docker inspect tattoo_studio_app
docker inspect tattoo_studio_db

- ACESSO RÁPIDO
# Abrir aplicação no navegador (Linux)
xdg-open http://localhost:5000
# Ver logs resumidos (últimas 50 linhas)
docker compose logs app --tail=50

- COMANDOS MAIS USADOS NO DIA A DIA:
# 1. Iniciar tudo
docker compose up -d --build
# 2. Ver se está funcionando
docker compose ps
# 3. Ver logs se houver problema
docker compose logs app -f
# 4. Parar tudo
docker compose down

---

