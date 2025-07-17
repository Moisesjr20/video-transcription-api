# 🚀 Script de Deploy para Easypanel (PowerShell)
# ===============================================

Write-Host "🎬 DEPLOY NO EASYPANEL - VIDEO TRANSCRIPTION API" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Função para imprimir com cor
function Write-Status {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Blue
}

# Verificar se estamos no diretório correto
if (-not (Test-Path "app.py")) {
    Write-Error "Execute este script no diretório do projeto!"
    exit 1
}

Write-Status "Verificando arquivos do projeto..."

# Verificar arquivos essenciais
$requiredFiles = @("app.py", "requirements.txt", "Dockerfile", "easypanel.yml")
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Status "✓ $file encontrado"
    } else {
        Write-Error "✗ $file não encontrado"
        exit 1
    }
}

# Verificar se o git está configurado
try {
    git status | Out-Null
    Write-Status "Git configurado"
} catch {
    Write-Error "Git não está configurado neste diretório!"
    exit 1
}

Write-Status "Preparando deploy..."

# Verificar se há mudanças não commitadas
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Warning "Há mudanças não commitadas!"
    Write-Host "Arquivos modificados:" -ForegroundColor Yellow
    git status --porcelain
    
    $response = Read-Host "Deseja fazer commit das mudanças? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        git add .
        git commit -m "Deploy: Add environment variables support"
        Write-Status "Commit realizado!"
    } else {
        Write-Warning "Deploy continuará com mudanças não commitadas"
    }
}

# Fazer push para o repositório
Write-Info "Fazendo push para o repositório..."
try {
    git push origin main
    Write-Status "Push realizado com sucesso!"
} catch {
    Write-Error "Erro ao fazer push!"
    exit 1
}

Write-Host ""
Write-Host "🎯 PRÓXIMOS PASSOS NO EASYPANEL:" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

Write-Info "1. Acesse seu painel Easypanel"
Write-Info "2. Clique em 'New Project'"
Write-Info "3. Selecione 'Git Repository'"
Write-Info "4. Cole a URL do seu repositório"
Write-Info "5. Clique em 'Create Project'"

Write-Host ""
Write-Host "🔧 CONFIGURAÇÃO DE VARIÁVEIS DE AMBIENTE:" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host @"
No Easypanel, adicione estas variáveis de ambiente:

GOOGLE_CLIENT_ID=1051222617815-jmdb2igpmhu4vhuhn92advr20qacj9vt.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
GOOGLE_REDIRECT_URI=https://seu-dominio.com/auth/callback
GOOGLE_DRIVE_FOLDER_ID=14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG
DESTINATION_EMAIL=seu-email@gmail.com
BUILD_DATE=2024-01-15
"@ -ForegroundColor White

Write-Host ""
Write-Host "🌐 CONFIGURAÇÃO DO GOOGLE CLOUD CONSOLE:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Info "1. Acesse: https://console.cloud.google.com/"
Write-Info "2. Vá em 'APIs & Services' → 'Credentials'"
Write-Info "3. Clique no seu OAuth 2.0 Client ID"
Write-Info "4. Em 'Authorized redirect URIs', adicione:"
Write-Host "   - https://seu-dominio.com/auth/callback" -ForegroundColor White
Write-Host "   - https://seu-dominio.com/" -ForegroundColor White
Write-Host "   - https://www.seu-dominio.com/auth/callback" -ForegroundColor White
Write-Host "   - https://www.seu-dominio.com/" -ForegroundColor White

Write-Host ""
Write-Host "📱 TESTE APÓS O DEPLOY:" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Cyan

Write-Info "1. Acesse: https://seu-dominio.com"
Write-Info "2. Teste a conexão Google"
Write-Info "3. Configure o monitoramento"
Write-Info "4. Adicione vídeos à pasta do Google Drive"

Write-Host ""
Write-Status "Deploy preparado com sucesso!"
Write-Info "Siga os passos acima no Easypanel para completar o deploy."

Write-Host ""
Write-Host "📋 RESUMO:" -ForegroundColor Cyan
Write-Host "=========" -ForegroundColor Cyan
Write-Host "✅ Repositório atualizado" -ForegroundColor Green
Write-Host "✅ Arquivos verificados" -ForegroundColor Green
Write-Host "✅ Push realizado" -ForegroundColor Green
Write-Host "⏳ Aguardando configuração no Easypanel" -ForegroundColor Yellow
Write-Host "⏳ Aguardando configuração no Google Console" -ForegroundColor Yellow

Write-Host ""
Write-Warning "IMPORTANTE: Substitua 'seu-dominio.com' pela sua URL real!"
Write-Warning "IMPORTANTE: Substitua 'seu-email@gmail.com' pelo seu email real!"

Write-Host ""
Write-Host "🎉 Pronto! Agora você pode configurar no Easypanel!" -ForegroundColor Green 