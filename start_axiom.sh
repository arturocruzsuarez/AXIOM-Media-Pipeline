#!/bin/bash

# ==========================================
# --- 1. CONFIGURACIÓN ---
# ==========================================
VENV_PATH="venv" 
SESSION="axiom_pipeline"

echo "🧹 Limpiando procesos anteriores de AXIOM..."
# Mata la sesión de tmux anterior si existe (silencia el error si no existe)
tmux kill-session -t $SESSION 2>/dev/null

# Mata cualquier Worker o Beat rebelde que haya quedado huérfano
pkill -f "celery -A AXIOM" 2>/dev/null

# Limpia la cola de Redis para no procesar basura vieja
redis-cli flushall 2>/dev/null
echo "✨ Limpieza completada. Iniciando ignición..."

# ==========================================
# --- 2. INICIAR SESIÓN TMUX ---
# ==========================================
tmux new-session -d -s $SESSION

# Función para preparar cada ventana (Entrar a la carpeta y activar venv)
prepare_window() {
    tmux send-keys -t $SESSION:$1 "cd $(pwd) && source $VENV_PATH/bin/activate" C-m
}

# ==========================================
# --- 3. CONFIGURAR VENTANAS ---
# ==========================================

# Ventana 0: Django
tmux rename-window -t $SESSION:0 'Django'
prepare_window 0
tmux send-keys -t $SESSION:0 "python3 manage.py runserver" C-m

# Ventana 1: Redis
tmux new-window -t $SESSION:1 -n 'Redis'
tmux send-keys -t $SESSION:1 "redis-server" C-m

# Ventana 2: Worker
tmux new-window -t $SESSION:2 -n 'Worker'
prepare_window 2
tmux send-keys -t $SESSION:2 "celery -A AXIOM worker -l info" C-m

# Ventana 3: Beat
tmux new-window -t $SESSION:3 -n 'Beat'
prepare_window 3
tmux send-keys -t $SESSION:3 "celery -A AXIOM beat -l info" C-m

# ==========================================
# --- 4. CONECTAR A LA SESIÓN ---
# ==========================================
tmux select-window -t $SESSION:0
tmux attach-session -t $SESSION