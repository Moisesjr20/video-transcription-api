# 🔧 Configuração do Monitoramento Automático

## 📋 Pré-requisitos

1. **Conta Google** com acesso ao Drive e Gmail
2. **Projeto no Google Cloud Console**
3. **APIs habilitadas**: Google Drive API e Gmail API
4. **Credenciais OAuth2** configuradas

## 🚀 Passo a Passo da Configuração

### 1. Configurar Google Cloud Console

#### 1.1 Criar/Selecionar Projeto
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Anote o **Project ID**

#### 1.2 Habilitar APIs
1. No menu lateral, vá em **APIs & Services** → **Library**
2. Procure e habilite:
   - **Google Drive API**
   - **Gmail API**

#### 1.3 Configurar OAuth2
1. Vá em **APIs & Services** → **Credentials**
2. Clique em **+ CREATE CREDENTIALS** → **OAuth 2.0 Client IDs**
3. Configure:
   - **Application type**: Desktop application
   - **Name**: Video Transcription API
4. Clique em **CREATE**
5. **Anote** o Client ID e Client Secret

### 2. Configurar Credenciais no Projeto

#### 2.1 Editar `google_config.py`
```python
# Substitua com suas credenciais
GOOGLE_CLIENT_ID = "1051222617815-jmdb2igpmhu4vhuhn92advr20qacj9vt.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

# ID da pasta do Google Drive (já configurado)
GOOGLE_DRIVE_FOLDER_ID = "14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG"

# Seu email para receber transcrições
DESTINATION_EMAIL = "seu-email-real@gmail.com"  # ⚠️ ALTERE AQUI
```

#### 2.2 Verificar URL de Redirecionamento
A URL de redirecionamento está configurada como:
```
http://localhost:8000/auth/callback
```

**Para produção**, você precisará:
1. Adicionar sua URL de produção no Google Console
2. Atualizar `GOOGLE_REDIRECT_URI` no `google_config.py`

### 3. Configurar URIs de Redirecionamento

#### 3.1 No Google Console
1. Vá em **APIs & Services** → **Credentials**
2. Clique no seu OAuth 2.0 Client ID
3. Em **Authorized redirect URIs**, adicione:
   - `http://localhost:8000/auth/callback` (desenvolvimento)
   - `https://seu-dominio.com/auth/callback` (produção)

### 4. Testar Configuração

#### 4.1 Executar Script de Setup
```bash
python setup_google_auth.py
```

O script irá:
- ✅ Testar conexão com API
- 🔐 Gerar URL de autenticação
- 📧 Testar envio de email
- 🚀 Iniciar monitoramento

#### 4.2 Testes Manuais
```bash
# Testar conexão com Google APIs
curl "http://localhost:8000/google/test-connection"

# Enviar email de teste
curl -X POST "http://localhost:8000/google/send-test-email" \
  -H "Content-Type: application/json" \
  -d '{"email": "seu-email@gmail.com"}'

# Verificar status do monitoramento
curl "http://localhost:8000/monitor/status"
```

## 🔄 Como Funciona o Monitoramento

### Fluxo Automático
1. **Verificação periódica**: A cada 5 minutos
2. **Detecção de vídeos**: Novos arquivos na pasta configurada
3. **Processamento**: Transcrição automática via Whisper AI
4. **Envio por email**: Resultado formatado em HTML

### Arquivos Processados
- ✅ **Suportados**: MP4, AVI, MOV, MKV, WMV, FLV, WEBM
- ❌ **Ignorados**: Arquivos muito grandes (>500MB)
- 🔄 **Rastreamento**: Lista de arquivos já processados

### Formato do Email
```html
🎬 Transcrição Automática Concluída

📁 Arquivo: video-reuniao.mp4
📅 Data: 15/01/2024 14:30
⏱️ Duração: 45:30
📏 Tamanho: 125.5 MB

📝 Transcrição:
[Transcrição completa aqui...]

Task ID: abc123-def456
```

## 🛠️ Troubleshooting

### Problema: "Erro de autenticação"
**Solução**:
1. Verifique se as credenciais estão corretas
2. Execute `python setup_google_auth.py` novamente
3. Verifique se as APIs estão habilitadas

### Problema: "Email não enviado"
**Solução**:
1. Verifique se o Gmail API está habilitado
2. Teste com `curl "http://localhost:8000/google/test-connection"`
3. Verifique se o email de destino está correto

### Problema: "Pasta não encontrada"
**Solução**:
1. Verifique se o `GOOGLE_DRIVE_FOLDER_ID` está correto
2. Confirme se a pasta é acessível
3. Teste com `curl "http://localhost:8000/monitor/check-now"`

### Problema: "Monitoramento não inicia"
**Solução**:
1. Verifique logs: `docker logs video-transcription-api`
2. Teste conexão: `curl "http://localhost:8000/health"`
3. Reinicie o container se necessário

## 📊 Monitoramento e Logs

### Logs Importantes
```bash
# Logs da API
docker logs video-transcription-api

# Logs específicos do monitoramento
docker logs video-transcription-api | grep "monitor"

# Status em tempo real
curl "http://localhost:8000/monitor/status"
```

### Métricas de Monitoramento
- **Arquivos processados**: Contador de sucessos
- **Tempo de processamento**: Por arquivo
- **Taxa de erro**: Falhas vs sucessos
- **Última verificação**: Timestamp

## 🔒 Segurança

### Boas Práticas
1. **Não compartilhe** suas credenciais
2. **Use variáveis de ambiente** em produção
3. **Monitore** logs regularmente
4. **Atualize** credenciais periodicamente

### Configuração de Produção
```bash
# Variáveis de ambiente
export GOOGLE_CLIENT_ID="seu-client-id"
export GOOGLE_CLIENT_SECRET="sua-client-secret"
export DESTINATION_EMAIL="seu-email@gmail.com"
```

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs primeiro
2. Execute os testes de conexão
3. Consulte esta documentação
4. Verifique configurações do Google Console

---

**Configuração concluída! 🎉** O monitoramento automático está pronto para processar seus vídeos. 