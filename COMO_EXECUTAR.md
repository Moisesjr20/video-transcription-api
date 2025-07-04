# 🚀 Como Executar a API Melhorada

## 📋 Pré-requisitos

1. **Python 3.7+** instalado
2. **Dependências** instaladas (ver seção abaixo)

## 🔧 Instalação das Dependências

### **Opção 1: Instalação completa (recomendada)**
```bash
pip install -r requirements.txt
```

### **Opção 2: Apenas para demonstração**
```bash
pip install fastapi uvicorn requests pydantic
```

## 🚀 Executar a API

### **1. Iniciar o servidor**
```bash
# Produção
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000

# Desenvolvimento (com reload automático)
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### **2. Verificar se está funcionando**
Abra no navegador: http://localhost:8000

Você deve ver:
```json
{
  "message": "Video Transcription API",
  "version": "1.2.0",
  "description": "API para transcrição de vídeos com processamento assíncrono..."
}
```

## 🧪 Testar a API

### **1. Testar com curl**
```bash
# Iniciar transcrição
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video.mp4",
    "language": "pt"
  }'

# Verificar status (substitua TASK_ID pelo ID retornado)
curl "http://localhost:8000/status/TASK_ID"

# Listar todas as tarefas
curl "http://localhost:8000/tasks"
```

### **2. Testar com Python**
```python
import requests
import time

# Iniciar transcrição
response = requests.post("http://localhost:8000/transcribe", json={
    "url": "https://example.com/video.mp4",
    "language": "pt"
})

if response.status_code == 200:
    result = response.json()
    task_id = result["task_id"]
    print(f"Task ID: {task_id}")
    
    # Monitorar progresso
    while True:
        status_response = requests.get(f"http://localhost:8000/status/{task_id}")
        status = status_response.json()
        
        print(f"Status: {status['status']} - {status['progress']*100:.1f}%")
        print(f"Mensagem: {status['message']}")
        
        if status['status'] in ['sucesso', 'erro']:
            break
        
        time.sleep(5)
```

### **3. Demonstração interativa**
```bash
# Execute o script de demonstração
python3 demo_api.py
```

## 📊 Documentação da API

### **Swagger UI (Interface visual)**
- Acesse: http://localhost:8000/docs
- Interface completa para testar todos os endpoints

### **ReDoc (Documentação)**
- Acesse: http://localhost:8000/redoc
- Documentação detalhada da API

## 🔍 Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/transcribe` | Inicia transcrição (resposta imediata) |
| `GET` | `/status/{task_id}` | Verifica status da transcrição |
| `GET` | `/download/{filename}` | Baixa arquivo de transcrição |
| `GET` | `/tasks` | Lista todas as tarefas |
| `DELETE` | `/tasks/{task_id}` | Remove uma tarefa |

## 🔄 Fluxo de Uso

```
1. POST /transcribe
   ↓ (resposta imediata)
   ✅ Retorna task_id

2. GET /status/{task_id}
   ↓ (verificar várias vezes)
   📊 Status: em_progresso

3. GET /status/{task_id}
   ↓ (quando concluído)
   🎉 Status: sucesso + transcrição
```

## 🛠️ Troubleshooting

### **Erro: "Module not found"**
```bash
# Instalar dependências
pip install -r requirements.txt
```

### **Erro: "Port already in use"**
```bash
# Usar porta diferente
python3 -m uvicorn app:app --host 0.0.0.0 --port 8001
```

### **Erro: "Permission denied"**
```bash
# Dar permissão aos diretórios
chmod 755 temp downloads transcriptions tasks
```

### **API não responde**
```bash
# Verificar se está rodando
curl http://localhost:8000/

# Verificar logs
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level debug
```

## 📁 Estrutura de Arquivos

```
seu_projeto/
├── app.py                 # API principal
├── requirements.txt       # Dependências
├── tasks/                 # Status das tarefas (JSON)
├── temp/                  # Arquivos temporários
├── downloads/             # Downloads de vídeos
├── transcriptions/        # Transcrições finais
├── exemplo_uso_api.py     # Exemplo de uso
└── demo_api.py           # Demonstração interativa
```

## 🎯 Pronto para Usar!

Sua API está agora **completamente funcional** com:
- ✅ Processamento assíncrono
- ✅ Status em tempo real
- ✅ Persistência de dados
- ✅ Interface amigável
- ✅ Documentação completa

**Divirta-se testando!** 🚀