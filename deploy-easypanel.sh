#!/bin/bash

# 🚀 Script de Deploy para Easypanel
# ===================================

echo "🎬 DEPLOY NO EASYPANEL - VIDEO TRANSCRIPTION API"
echo "================================================"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir com cor
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Verificar se estamos no diretório correto
if [ ! -f "app.py" ]; then
    print_error "Execute este script no diretório do projeto!"
    exit 1
fi

print_status "Verificando arquivos do projeto..."

# Verificar arquivos essenciais
required_files=("app.py" "requirements.txt" "Dockerfile" "easypanel.yml")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_status "✓ $file encontrado"
    else
        print_error "✗ $file não encontrado"
        exit 1
    fi
done

# Verificar se o git está configurado
if ! git status > /dev/null 2>&1; then
    print_error "Git não está configurado neste diretório!"
    exit 1
fi

print_status "Preparando deploy..."

# Verificar se há mudanças não commitadas
if [ -n "$(git status --porcelain)" ]; then
    print_warning "Há mudanças não commitadas!"
    echo "Arquivos modificados:"
    git status --porcelain
    
    read -p "Deseja fazer commit das mudanças? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "Deploy: Add environment variables support"
        print_status "Commit realizado!"
    else
        print_warning "Deploy continuará com mudanças não commitadas"
    fi
fi

# Fazer push para o repositório
print_info "Fazendo push para o repositório..."
if git push origin main; then
    print_status "Push realizado com sucesso!"
else
    print_error "Erro ao fazer push!"
    exit 1
fi

echo
echo "🎯 PRÓXIMOS PASSOS NO EASYPANEL:"
echo "================================"

print_info "1. Acesse seu painel Easypanel"
print_info "2. Clique em 'New Project'"
print_info "3. Selecione 'Git Repository'"
print_info "4. Cole a URL do seu repositório"
print_info "5. Clique em 'Create Project'"

echo
echo "🔧 CONFIGURAÇÃO DE VARIÁVEIS DE AMBIENTE:"
echo "========================================="

cat << 'EOF'
No Easypanel, adicione estas variáveis de ambiente:

GOOGLE_CLIENT_ID=1051222617815-jmdb2igpmhu4vhuhn92advr20qacj9vt.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
GOOGLE_REDIRECT_URI=https://seu-dominio.com/auth/callback
GOOGLE_DRIVE_FOLDER_ID=14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG
DESTINATION_EMAIL=seu-email@gmail.com
BUILD_DATE=2024-01-15
EOF

echo
echo "🌐 CONFIGURAÇÃO DO GOOGLE CLOUD CONSOLE:"
echo "========================================"

print_info "1. Acesse: https://console.cloud.google.com/"
print_info "2. Vá em 'APIs & Services' → 'Credentials'"
print_info "3. Clique no seu OAuth 2.0 Client ID"
print_info "4. Em 'Authorized redirect URIs', adicione:"
echo "   - https://seu-dominio.com/auth/callback"
echo "   - https://seu-dominio.com/"
echo "   - https://www.seu-dominio.com/auth/callback"
echo "   - https://www.seu-dominio.com/"

echo
echo "📱 TESTE APÓS O DEPLOY:"
echo "======================="

print_info "1. Acesse: https://seu-dominio.com"
print_info "2. Teste a conexão Google"
print_info "3. Configure o monitoramento"
print_info "4. Adicione vídeos à pasta do Google Drive"

echo
print_status "Deploy preparado com sucesso!"
print_info "Siga os passos acima no Easypanel para completar o deploy."

echo
echo "📋 RESUMO:"
echo "========="
echo "✅ Repositório atualizado"
echo "✅ Arquivos verificados"
echo "✅ Push realizado"
echo "⏳ Aguardando configuração no Easypanel"
echo "⏳ Aguardando configuração no Google Console"

echo
print_warning "IMPORTANTE: Substitua 'seu-dominio.com' pela sua URL real!"
print_warning "IMPORTANTE: Substitua 'seu-email@gmail.com' pelo seu email real!" 