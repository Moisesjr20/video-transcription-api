# Configuração das Novas Credenciais OAuth

## 🔑 Credenciais Configuradas

Suas novas credenciais foram configuradas no código:

```
GOOGLE_CLIENT_ID=1051222617815-rm2gm4e24d7ig8mb1fq6kbjq1hs4ppds.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
GOOGLE_REDIRECT_URI=https://transcritor-transcritor.whhc5g.easypanel.host/auth/callback
```

## 🔧 Configuração no Google Cloud Console

### 1. Acessar o Google Cloud Console

1. Acesse: https://console.cloud.google.com/
2. Selecione seu projeto
3. Vá para **APIs & Services** > **Credentials**

### 2. Configurar Credenciais OAuth 2.0

1. Encontre suas credenciais OAuth 2.0 ou crie novas
2. Clique em **Edit** (editar)
3. Configure os seguintes campos:

#### Tipo de Aplicativo
- **Application type**: Web application

#### URIs de Redirecionamento Autorizadas
Adicione estas URIs:
```
https://transcritor-transcritor.whhc5g.easypanel.host/auth/callback
https://transcritor-transcritor.whhc5g.easypanel.host/google/complete-auth
```

### 3. Habilitar APIs Necessárias

Vá para **APIs & Services** > **Library** e habilite:

1. **Google Drive API**
2. **Gmail API**
3. **Google+ API** (pode ser necessário para OAuth)

### 4. Configurar Tela de Consentimento OAuth

Vá para **APIs & Services** > **OAuth consent screen**:

1. Configure a tela de consentimento
2. Adicione os seguintes escopos:
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.compose`

### 5. Configurar Variáveis de Ambiente no Easypanel

No Easypanel, configure estas variáveis de ambiente:

```bash
GOOGLE_CLIENT_ID=1051222617815-rm2gm4e24d7ig8mb1fq6kbjq1hs4ppds.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
GOOGLE_REDIRECT_URI=https://transcritor-transcritor.whhc5g.easypanel.host/auth/callback
```

## 🧪 Teste das Credenciais

### 1. Teste Local

Execute o script de teste:
```bash
python test_new_credentials.py
```

### 2. Teste no Easypanel

1. Faça deploy da aplicação no Easypanel
2. Acesse: `https://transcritor-transcritor.whhc5g.easypanel.host/auth-setup`
3. Clique em "Gerar URL de Autenticação"
4. Teste a URL em modo incógnito

### 3. Verificar Logs

Se houver problemas, verifique os logs do Easypanel para identificar erros específicos.

## 🚨 Solução de Problemas

### Erro 400: invalid_request

**Causas comuns:**
1. **Redirect URI não autorizada** - Verifique se a URI está na lista do Google Console
2. **Client ID incorreto** - Confirme se o Client ID está correto
3. **APIs não habilitadas** - Verifique se as APIs estão habilitadas
4. **Escopos não configurados** - Configure os escopos na tela de consentimento

### Erro redirect_uri_mismatch

**Solução:**
1. Adicione a URI exata no Google Cloud Console
2. Verifique se não há espaços extras
3. Confirme se o protocolo é HTTPS

### Erro invalid_client

**Solução:**
1. Verifique se o Client ID está correto
2. Confirme se o tipo de aplicativo é "Web application"
3. Verifique se as credenciais não foram revogadas

## 📋 Checklist de Verificação

- [ ] Credenciais OAuth 2.0 configuradas no Google Cloud Console
- [ ] Tipo de aplicativo: "Web application"
- [ ] URIs de redirecionamento autorizadas configuradas
- [ ] APIs do Google Drive e Gmail habilitadas
- [ ] Tela de consentimento OAuth configurada
- [ ] Escopos necessários adicionados
- [ ] Variáveis de ambiente configuradas no Easypanel
- [ ] Aplicação deployada no Easypanel
- [ ] URL de autorização testada em modo incógnito

## 🔗 Links Úteis

- [Google Cloud Console](https://console.cloud.google.com/)
- [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
- [APIs & Services > OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
- [APIs & Services > Library](https://console.cloud.google.com/apis/library)

## 📞 Próximos Passos

1. **Configure as URIs de redirecionamento no Google Cloud Console**
2. **Habilite as APIs necessárias**
3. **Configure a tela de consentimento OAuth**
4. **Deploy a aplicação no Easypanel**
5. **Teste a autenticação OAuth**

---

**Nota**: Se o erro 400 persistir após seguir este guia, pode ser necessário:
1. Criar novas credenciais OAuth no Google Cloud Console
2. Verificar se há restrições de IP no projeto
3. Aguardar alguns minutos para as mudanças propagarem 