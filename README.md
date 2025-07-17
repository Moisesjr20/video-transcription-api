# 🤖 Transcritor Automático - Google Drive

Uma aplicação inteligente que monitora automaticamente uma pasta compartilhada do Google Drive e transcreve vídeos automaticamente usando IA.

## ✨ Funcionalidades

- **🔍 Monitoramento Automático**: Verifica periodicamente uma pasta do Google Drive
- **🎬 Transcrição Inteligente**: Usa Whisper AI para transcrições precisas
- **📧 Notificações por Email**: Envia transcrições automaticamente por email
- **🌐 Interface Web Moderna**: Dashboard intuitivo para controle e monitoramento
- **⚡ Processamento Assíncrono**: Não trava a aplicação durante transcrições
- **📊 Histórico Completo**: Mantém registro de todas as transcrições

## 🚀 Como Funciona

1. **Configuração**: Configure as credenciais do Google e email de destino
2. **Monitoramento**: A aplicação verifica a pasta a cada 5 minutos
3. **Detecção**: Novos vídeos são automaticamente identificados
4. **Transcrição**: Vídeos são baixados e transcritos usando Whisper AI
5. **Notificação**: Transcrições são enviadas por email automaticamente

## 📁 Pasta Monitorada

A aplicação monitora esta pasta do Google Drive:
[📁 Pasta de Vídeos](https://drive.google.com/drive/folders/14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG?usp=sharing)

## 🛠️ Tecnologias

- **Backend**: FastAPI + Python
- **IA**: OpenAI Whisper
- **Google APIs**: Drive + Gmail
- **Frontend**: HTML5 + CSS3 + JavaScript
- **Deploy**: Docker + Easypanel

## 📋 Pré-requisitos

- Python 3.8+
- Conta Google com APIs habilitadas
- Acesso à pasta compartilhada do Google Drive

## ⚙️ Configuração

### 1. Variáveis de Ambiente

Configure no Easypanel:

```env
GOOGLE_CLIENT_ID=seu_client_id
GOOGLE_CLIENT_SECRET=seu_client_secret
GOOGLE_REDIRECT_URI=https://seu-dominio.easypanel.host/auth/callback
GOOGLE_DRIVE_FOLDER_ID=14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG
DESTINATION_EMAIL=seu-email@gmail.com
```

### 2. Google Cloud Console

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione existente
3. Habilite as APIs:
   - Google Drive API
   - Gmail API
4. Configure OAuth 2.0:
   - Tipo: Aplicação Web
   - URIs autorizados: `https://seu-dominio.easypanel.host`
   - URIs de redirecionamento: `https://seu-dominio.easypanel.host/auth/callback`

### 3. Autenticação

1. Acesse a interface web
2. Clique em "Configurar Auth" na seção Google
3. Autorize o acesso às APIs
4. Teste a conexão

## 🎯 Uso

### Interface Web

Acesse a interface web para:

- **📊 Dashboard**: Visualizar status do monitoramento
- **🎛️ Controles**: Iniciar/parar monitoramento
- **🔍 Verificação Manual**: Verificar novos vídeos agora
- **📧 Teste de Email**: Enviar email de teste
- **📋 Histórico**: Ver transcrições recentes

### Monitoramento Automático

1. **Iniciar**: Clique em "Iniciar Monitoramento"
2. **Configurar**: O sistema verifica a pasta a cada 5 minutos
3. **Processar**: Novos vídeos são automaticamente transcritos
4. **Notificar**: Transcrições são enviadas por email

### Formatos Suportados

- **Vídeos**: MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V, 3GP
- **Tamanho Máximo**: 500 MB por arquivo
- **Idiomas**: Português (padrão), Inglês, Espanhol

## 📧 Emails Automáticos

Cada transcrição gera um email com:

- **📁 Nome do arquivo**
- **📅 Data e hora**
- **📏 Tamanho do arquivo**
- **📝 Transcrição completa**
- **🎨 Layout HTML responsivo**

## 🔧 Endpoints da API

### Monitoramento
- `POST /monitor/start` - Iniciar monitoramento
- `POST /monitor/stop` - Parar monitoramento
- `GET /monitor/status` - Status do monitoramento
- `POST /monitor/check-now` - Verificar agora

### Transcrição
- `POST /transcribe` - Iniciar transcrição manual
- `GET /status/{task_id}` - Status da transcrição
- `GET /tasks` - Listar todas as tarefas

### Google
- `GET /google/test-connection` - Testar conexão
- `GET /google/setup-auth` - Configurar autenticação
- `POST /google/send-test-email` - Enviar email de teste

## 🐳 Deploy com Docker

```bash
# Build da imagem
docker build -t transcritor-automatico .

# Executar container
docker run -d \
  -p 8000:8000 \
  -e GOOGLE_CLIENT_ID=seu_id \
  -e GOOGLE_CLIENT_SECRET=seu_secret \
  -e DESTINATION_EMAIL=seu@email.com \
  transcritor-automatico
```

## 📊 Monitoramento

### Logs
- **🔍 Verificação**: Logs de verificação da pasta
- **🎬 Processamento**: Status de cada vídeo processado
- **📧 Email**: Confirmação de envio de emails
- **❌ Erros**: Detalhes de erros e falhas

### Métricas
- **📹 Vídeos Processados**: Contador total
- **⏰ Última Verificação**: Timestamp da última verificação
- **📊 Status**: Ativo/Inativo
- **📧 Conexão Google**: Drive e Gmail

## 🔒 Segurança

- **🔐 OAuth 2.0**: Autenticação segura do Google
- **📁 Arquivos Temporários**: Limpeza automática
- **🔒 Variáveis de Ambiente**: Credenciais protegidas
- **🌐 HTTPS**: Comunicação criptografada

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

## 📈 Versões

- **v2.0.0**: Monitoramento automático completo
- **v1.3.8**: API de transcrição manual
- **v1.0.0**: Versão inicial

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para detalhes.

## 📞 Suporte

Para suporte ou dúvidas:
- 📧 Email: [seu-email@gmail.com]
- 🐛 Issues: [GitHub Issues]
- 📖 Documentação: [Wiki do Projeto]

---

**🎉 Transforme sua pasta do Google Drive em um sistema inteligente de transcrição!** 