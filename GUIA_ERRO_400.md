# Guia para Resolver Erro OAuth 400: invalid_request

## 🔍 Diagnóstico do Problema

O erro **400: invalid_request** no OAuth 2.0 do Google indica que há um problema com os parâmetros da requisição de autorização. Baseado na [documentação oficial do Google](https://developers.google.com/identity/protocols/oauth2?hl=pt-br), este erro pode ter várias causas.

## 📋 Checklist de Verificação

### 1. ✅ Verificar Variáveis de Ambiente no Easypanel

Certifique-se de que estas variáveis estão configuradas corretamente no Easypanel:

```bash
GOOGLE_CLIENT_ID=seu-client-id-aqui
GOOGLE_CLIENT_SECRET=seu-client-secret-aqui
GOOGLE_REDIRECT_URI=https://seu-dominio.com/auth/callback
```

### 2. ✅ Verificar Google Cloud Console

#### 2.1 Credenciais OAuth 2.0
- Acesse: https://console.cloud.google.com/apis/credentials
- Verifique se o **Client ID** está correto
- Confirme que o tipo é **"Web application"**
- Verifique se a **Redirect URI** está na lista de URIs autorizadas

#### 2.2 URIs de Redirecionamento Autorizadas
Adicione estas URIs no Google Cloud Console:
```
https://seu-dominio.com/auth/callback
https://seu-dominio.com/google/complete-auth
```

#### 2.3 APIs Habilitadas
Verifique se estas APIs estão habilitadas:
- Google Drive API
- Gmail API
- Google+ API (pode ser necessário)

### 3. ✅ Verificar Tela de Consentimento OAuth

- Acesse: https://console.cloud.google.com/apis/credentials/consent
- Configure a tela de consentimento
- Adicione os escopos necessários:
  - `https://www.googleapis.com/auth/drive.readonly`
  - `https://www.googleapis.com/auth/gmail.send`
  - `https://www.googleapis.com/auth/gmail.compose`

### 4. ✅ Verificar Parâmetros da URL de Autorização

A URL deve conter estes parâmetros obrigatórios:

```python
params = {
    "response_type": "code",
    "client_id": "SEU_CLIENT_ID",
    "redirect_uri": "https://seu-dominio.com/auth/callback",
    "scope": "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.compose",
    "access_type": "offline",
    "prompt": "consent",
    "include_granted_scopes": "true"
}
```

## 🔧 Soluções Específicas

### Solução 1: Limpar Cache e Sessões

1. **Limpar cache do navegador**
2. **Usar modo incógnito**
3. **Reiniciar o servidor no Easypanel**
4. **Gerar nova URL de autorização**

### Solução 2: Verificar Formato do Client ID

O Client ID deve ter o formato:
```
123456789-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com
```

### Solução 3: Verificar Redirect URI

A URI de redirecionamento deve:
- Usar HTTPS (exceto para localhost)
- Estar exatamente igual no código e no Google Console
- Não ter fragmentos (#)
- Ter um caminho válido

### Solução 4: Verificar Escopos

Os escopos devem estar:
- Separados por espaço
- URL-encoded corretamente
- Incluídos na tela de consentimento

## 🚨 Causas Comuns do Erro 400

### 1. **Redirect URI não autorizada**
```
Erro: redirect_uri_mismatch
Solução: Adicionar URI no Google Cloud Console
```

### 2. **Client ID inválido**
```
Erro: invalid_client
Solução: Verificar se o Client ID está correto
```

### 3. **Escopos malformados**
```
Erro: invalid_scope
Solução: Verificar formato dos escopos
```

### 4. **Parâmetros duplicados**
```
Erro: invalid_request
Solução: Remover parâmetros duplicados da URL
```

### 5. **State muito longo**
```
Erro: invalid_request
Solução: Reduzir tamanho do parâmetro state
```

## 🔍 Debug Avançado

### Testar URL Manualmente

1. Gere a URL de autorização
2. Copie a URL completa
3. Abra em modo incógnito
4. Verifique se há erros na URL

### Verificar Logs do Servidor

Execute este comando para ver logs detalhados:
```bash
python oauth_debug.py
```

### Testar Configuração

Execute este comando para testar a configuração:
```bash
python test_oauth_400.py
```

## 📞 Próximos Passos

1. **Verifique as variáveis de ambiente no Easypanel**
2. **Confirme as configurações no Google Cloud Console**
3. **Limpe o cache do navegador**
4. **Teste com uma nova URL de autorização**
5. **Se o problema persistir, verifique os logs do servidor**

## 🔗 Links Úteis

- [Google Cloud Console](https://console.cloud.google.com/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2?hl=pt-br)
- [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)

## 📝 Exemplo de URL Correta

```
https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=SEU_CLIENT_ID&redirect_uri=https://seu-dominio.com/auth/callback&scope=https%3A//www.googleapis.com/auth/drive.readonly%20https%3A//www.googleapis.com/auth/gmail.send%20https%3A//www.googleapis.com/auth/gmail.compose&access_type=offline&prompt=consent&include_granted_scopes=true&state=random_state_123
```

---

**Nota**: Se o problema persistir após seguir este guia, pode ser necessário:
1. Criar novas credenciais OAuth no Google Cloud Console
2. Verificar se há restrições de IP no projeto
3. Contatar o suporte do Google Cloud se necessário 