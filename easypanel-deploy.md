# 🚀 Deploy no Easypanel - Guia Completo

## 📋 Pré-requisitos

1. **Conta Easypanel** configurada
2. **Repositório Git** com o código
3. **Google Cloud Console** configurado
4. **Domínio** apontando para o VPS

## 🎯 Passo a Passo do Deploy

### 1. **Preparar o Repositório**
```bash
# Commit das alterações
git add .
git commit -m "Add environment variables support"
git push origin main
```

### 2. **Criar Projeto no Easypanel**
1. Acesse seu painel Easypanel
2. Clique em **New Project**
3. Selecione **Git Repository**
4. Cole a URL do seu repositório
5. Clique em **Create Project**

### 3. **Configurar Variáveis de Ambiente**

No Easypanel, vá em **Environment Variables** e adicione:

```bash
# Google OAuth2 Configuration
GOOGLE_CLIENT_ID=1051222617815-jmdb2igpmhu4vhuhn92advr20qacj9vt.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# Redirect URI (será sua URL do VPS)
GOOGLE_REDIRECT_URI=https://seu-dominio.com/auth/callback

# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG

# Email Configuration
DESTINATION_EMAIL=seu-email@gmail.com

# Build Configuration
BUILD_DATE=2024-01-15
```

### 4. **Configurar Domínio**
1. No Easypanel, vá em **Domains**
2. Adicione seu domínio: `seu-dominio.com`
3. Configure SSL se necessário

### 5. **Configurar Google Cloud Console**

#### 5.1 Acessar Google Cloud Console
- Vá para: https://console.cloud.google.com/
- Selecione seu projeto

#### 5.2 Configurar OAuth2
1. **APIs & Services** → **Credentials**
2. Clique no seu **OAuth 2.0 Client ID**
3. Em **Authorized redirect URIs**, adicione:
   ```
   https://seu-dominio.com/auth/callback
   https://seu-dominio.com/
   ```

#### 5.3 URLs para Adicionar
```
https://seu-dominio.com/auth/callback
https://seu-dominio.com/
https://www.seu-dominio.com/auth/callback
https://www.seu-dominio.com/
```

### 6. **Deploy e Teste**

#### 6.1 Fazer Deploy
1. No Easypanel, clique em **Deploy**
2. Aguarde o build completar
3. Verifique os logs se houver erro

#### 6.2 Testar Interface
1. Acesse: `https://seu-dominio.com`
2. Verifique se a interface carrega
3. Teste a conexão Google

## 🔧 Configuração Avançada

### Porta e Recursos
```yaml
# easypanel.yml (se necessário)
services:
  - name: video-transcription-api
    image: python:3.11-slim
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI}
      - GOOGLE_DRIVE_FOLDER_ID=${GOOGLE_DRIVE_FOLDER_ID}
      - DESTINATION_EMAIL=${DESTINATION_EMAIL}
    volumes:
      - ./:/app
    working_dir: /app
    command: uvicorn app:app --host 0.0.0.0 --port 8000
```

### Health Check
```bash
# Testar se está funcionando
curl https://seu-dominio.com/health
```

## 🚨 Troubleshooting

### Problema: Deploy falha
**Solução**:
1. Verifique os logs no Easypanel
2. Confirme se todas as variáveis estão configuradas
3. Verifique se o repositório está atualizado

### Problema: Interface não carrega
**Solução**:
1. Verifique se o domínio está configurado
2. Teste: `curl https://seu-dominio.com/health`
3. Verifique SSL se necessário

### Problema: Google OAuth não funciona
**Solução**:
1. Confirme se as URLs estão no Google Console
2. Verifique se `GOOGLE_REDIRECT_URI` está correto
3. Teste a autenticação

## 📊 Monitoramento

### Logs no Easypanel
1. Vá em **Logs** no projeto
2. Monitore erros e warnings
3. Verifique uso de recursos

### Métricas
- **CPU**: Deve ficar baixo em idle
- **RAM**: ~500MB-1GB em uso
- **Disco**: ~2-5GB para transcrições

## 🔐 Segurança

### Variáveis Sensíveis
- ✅ **GOOGLE_CLIENT_SECRET**: Mantenha seguro
- ✅ **DESTINATION_EMAIL**: Use email real
- ✅ **GOOGLE_REDIRECT_URI**: URL exata do VPS

### SSL/HTTPS
- Configure SSL no Easypanel
- Use sempre HTTPS para OAuth
- Verifique certificados

## 🎉 Após o Deploy

### 1. Testar Interface
```
https://seu-dominio.com
```

### 2. Configurar Monitoramento
1. Acesse a interface
2. Clique em "Testar Conexão Google"
3. Configure autenticação se necessário
4. Inicie o monitoramento

### 3. Adicionar Vídeos
1. Adicione vídeos à pasta do Google Drive
2. Monitore os logs de atividade
3. Verifique recebimento de emails

## 📱 URLs Finais

### Interface Web
```
https://seu-dominio.com
```

### API Endpoints
```
https://seu-dominio.com/health
https://seu-dominio.com/monitor/status
https://seu-dominio.com/google/test-connection
```

### Google OAuth
```
https://seu-dominio.com/auth/callback
```

---

**🎉 Deploy no Easypanel configurado! Agora você tem uma URL fixa e segura para o OAuth2!** 