# ⚡ Configuração Rápida - Transcritor Automático

Guia rápido para configurar e usar o Transcritor Automático.

## 🚀 Deploy no Easypanel

### 1. Criar Projeto
1. Acesse o Easypanel
2. Clique em "New Project"
3. Selecione "Git Repository"
4. Cole a URL do repositório
5. Clique em "Deploy"

### 2. Configurar Variáveis de Ambiente

No Easypanel, adicione estas variáveis:

```env
GOOGLE_CLIENT_ID=seu_client_id_aqui
GOOGLE_CLIENT_SECRET=seu_client_secret_aqui
GOOGLE_REDIRECT_URI=https://seu-dominio.easypanel.host/auth/callback
GOOGLE_DRIVE_FOLDER_ID=14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG
DESTINATION_EMAIL=seu-email@gmail.com
BUILD_DATE=2024-01-17
```

### 3. Configurar Google Cloud Console

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione existente
3. Habilite as APIs:
   - Google Drive API
   - Gmail API
4. Configure OAuth 2.0:
   - Tipo: Aplicação Web
   - URIs autorizados: `https://seu-dominio.easypanel.host`
   - URIs de redirecionamento: `https://seu-dominio.easypanel.host/auth/callback`

## 🔧 Configuração da Aplicação

### 1. Acessar Interface Web
- URL: `https://seu-dominio.easypanel.host`
- Aguarde o carregamento da interface

### 2. Configurar Autenticação Google
1. Na seção "Conexão Google"
2. Clique em "Configurar Auth"
3. Autorize o acesso às APIs
4. Teste a conexão

### 3. Iniciar Monitoramento
1. Na seção "Status do Monitoramento"
2. Clique em "Iniciar Monitoramento"
3. O sistema começará a verificar a pasta a cada 5 minutos

## 📁 Pasta Monitorada

A aplicação monitora automaticamente esta pasta:
[📁 Pasta de Vídeos](https://drive.google.com/drive/folders/14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG?usp=sharing)

## 🎯 Como Usar

### Adicionar Vídeos
1. Faça upload de vídeos para a pasta compartilhada
2. O sistema detectará automaticamente
3. Transcrição será iniciada em background
4. Email será enviado com a transcrição

### Formatos Suportados
- **Vídeos**: MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V, 3GP
- **Tamanho Máximo**: 500 MB por arquivo
- **Idiomas**: Português (padrão), Inglês, Espanhol

### Controles Disponíveis
- **🎛️ Iniciar/Parar**: Controle do monitoramento
- **🔍 Verificar Agora**: Verificação manual
- **📧 Teste de Email**: Enviar email de teste
- **📊 Status**: Visualizar métricas em tempo real

## 📧 Emails Automáticos

Cada transcrição gera um email com:
- **📁 Nome do arquivo**
- **📅 Data e hora**
- **📏 Tamanho do arquivo**
- **📝 Transcrição completa**
- **🎨 Layout HTML responsivo**

## 🚨 Troubleshooting

### Erro 400 OAuth
1. Verifique as URIs no Google Cloud Console
2. Confirme o redirect_uri nas variáveis de ambiente
3. Limpe o cache do navegador
4. Regenere as credenciais OAuth

### Vídeos não processados
1. Verifique o tamanho do arquivo (máx. 500MB)
2. Confirme se é um formato suportado
3. Verifique as permissões da pasta do Drive
4. Teste a conexão Google

### Emails não enviados
1. Teste a conexão Gmail
2. Verifique o email de destino
3. Confirme as permissões do Gmail API
4. Envie email de teste

## 📊 Monitoramento

### Logs Disponíveis
- **🔍 Verificação**: Logs de verificação da pasta
- **🎬 Processamento**: Status de cada vídeo processado
- **📧 Email**: Confirmação de envio de emails
- **❌ Erros**: Detalhes de erros e falhas

### Métricas em Tempo Real
- **📹 Vídeos Processados**: Contador total
- **⏰ Última Verificação**: Timestamp da última verificação
- **📊 Status**: Ativo/Inativo
- **📧 Conexão Google**: Drive e Gmail

## 🧪 Testes

Execute o script de teste para verificar se tudo está funcionando:

```bash
python test_app.py
```

## 📞 Suporte

Para suporte ou dúvidas:
- 📧 Email: [seu-email@gmail.com]
- 🐛 Issues: [GitHub Issues]
- 📖 Documentação: [Wiki do Projeto]

---

**🎉 Sua aplicação está pronta para monitorar e transcrever vídeos automaticamente!** 