# 🔐 Guia de Segurança - Transcritor API

## 🚨 Melhorias de Segurança Implementadas

### ✅ **Correções Críticas Aplicadas**

#### 1. **API Keys Seguras**
- ❌ **ANTES**: Chave hardcoded no código
- ✅ **DEPOIS**: Variáveis de ambiente com validação

#### 2. **Autenticação JWT**
- ❌ **ANTES**: API pública sem controle
- ✅ **DEPOIS**: Sistema de login com tokens JWT

#### 3. **Rate Limiting**
- ❌ **ANTES**: Sem proteção contra spam
- ✅ **DEPOIS**: 10 requisições/minuto por IP com SlowAPI

#### 4. **Validação de Entrada**
- ❌ **ANTES**: URLs não validadas
- ✅ **DEPOIS**: Validação rigorosa de URLs, extensões e tamanhos

#### 5. **Logs de Auditoria**
- ❌ **ANTES**: Logs básicos sem segurança
- ✅ **DEPOIS**: Logs detalhados de segurança em arquivo separado

#### 6. **Sanitização de Dados**
- ❌ **ANTES**: Vulnerável a path traversal
- ✅ **DEPOIS**: Validação de IDs e sanitização de nomes

## 🛡️ **Recursos de Segurança**

### **Autenticação e Autorização**
```python
# Usuários demo (ALTERE EM PRODUÇÃO!)
admin / admin123  # Acesso completo
user / user123    # Acesso à transcrição

# Scopes de permissão
"transcribe" - Pode criar transcrições
"admin" - Acesso administrativo completo
```

### **Rate Limiting**
```
Login: 20 req/min
Transcrição: 10 req/min
Status: 30 req/min
Health: 60 req/min
```

### **Validações Implementadas**
- URLs apenas do Google Drive
- Extensões: mp4, avi, mov, mkv, mp3, wav, m4a
- Tamanho máximo: 500MB
- IDs de tarefa: apenas alfanuméricos e hífens
- Timeouts: 10 minutos para transcrição

## 📋 **Checklist para Produção**

### **🔴 Crítico - Faça ANTES de publicar**
- [ ] Alterar senhas padrão dos usuários demo
- [ ] Configurar ASSEMBLYAI_API_KEY no .env
- [ ] Gerar chaves secretas fortes (32+ caracteres)
- [ ] Configurar HTTPS com certificados SSL
- [ ] Desabilitar docs em produção (DEBUG=false)

### **🟡 Importante - Próximos passos**
- [ ] Implementar banco de dados para usuários
- [ ] Configurar backup automático dos logs
- [ ] Implementar rotação de logs
- [ ] Configurar alertas de segurança
- [ ] Implementar métricas de uso

### **🟢 Recomendado - Melhorias futuras**
- [ ] Implementar 2FA para administradores
- [ ] Adicionar captcha para endpoints públicos
- [ ] Implementar blacklist de IPs
- [ ] Adicionar criptografia para dados sensíveis
- [ ] Implementar sessões de usuário

## 🚦 **Endpoints de Segurança**

### **Públicos (Rate Limited)**
- `GET /` - Interface web
- `GET /health` - Health check
- `GET /ping` - Status do servidor
- `POST /login` - Autenticação

### **Autenticados (JWT Required)**
- `POST /transcribe-secure` - Transcrição segura
- `GET /status-secure/{id}` - Status seguro

### **Admin Only**
- `GET /admin/tasks` - Lista todas as tarefas

### **Compatibilidade (Menos Seguro)**
- `POST /transcribe` - Transcrição pública
- `GET /status/{id}` - Status público (dados limitados)

## 📊 **Monitoramento**

### **Logs de Segurança**
```bash
# Localização dos logs
logs/app.log      # Logs gerais da aplicação
logs/security.log # Logs específicos de segurança

# Eventos monitorados
- Tentativas de login (sucesso/falha)
- Acessos a endpoints protegidos
- Violações de rate limit
- Tentativas de path traversal
- URLs inválidas ou suspeitas
- Erros de validação
```

### **Métricas Importantes**
- Taxa de tentativas de login falhadas
- Violações de rate limit por IP
- Erros de validação por endpoint
- Tempo de resposta dos endpoints
- Uso de recursos (CPU/Memória)

## 🆘 **Resposta a Incidentes**

### **Se detectar atividade suspeita:**
1. **Verifique os logs de segurança**
2. **Identifique o IP da origem**
3. **Bloqueie o IP no firewall se necessário**
4. **Revogue tokens JWT se comprometidos**
5. **Altere chaves secretas se necessário**
6. **Documente o incidente**

### **Contatos de Emergência**
- Administrador do Sistema: [seu-email@empresa.com]
- Equipe de Segurança: [security@empresa.com]
- Suporte Técnico: [support@empresa.com]

## 🔧 **Configurações Recomendadas**

### **Variáveis de Ambiente (.env)**
```env
# Obrigatórias
ASSEMBLYAI_API_KEY=sua_chave_real_aqui
API_SECRET_KEY=chave_secreta_minimo_32_caracteres
JWT_SECRET_KEY=chave_jwt_minimo_32_caracteres

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_MINUTES=1
MAX_CONCURRENT_TASKS=3

# Segurança
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Arquivo
MAX_FILE_SIZE_MB=500
ALLOWED_EXTENSIONS=mp4,avi,mov,mkv,mp3,wav,m4a
```

### **Docker Compose (Produção)**
```yaml
version: '3.8'
services:
  transcritor:
    build: .
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /app/temp
```

---

**⚠️ IMPORTANTE**: Esta API agora está significativamente mais segura, mas a segurança é um processo contínuo. Monitore regularmente e mantenha-se atualizado com as melhores práticas de segurança.